from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime , timedelta
import base64
import io
import xlsxwriter
import re

class HR_Sueldos(models.Model):
    _name = 'hr.sueldos'
    _description = 'Pago de sueldos'
    _inherit = ['mail.thread']
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Ya existe una nómina con este mes/año. No se puede crear duplicados.'),
    ]

    name = fields.Char(string='Mes', index=True)
    nomina_id = fields.One2many('hr.nomina', 'sueldo_id', string='Nómina')
    nomina_id_base = fields.One2many('hr.nomina', 'sueldo_base_id', string='Nómina')
    nomina_id_bonos = fields.One2many('hr.nomina', 'sueldo_bonos_id', string='Nómina de bonos')
    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    observaciones = fields.Html(string='Observaciones')
    excel_file = fields.Binary(string='Archivo Excel')
    file_name = fields.Char(string='Nombre del archivo')
    
    @api.model
    def create(self, vals):
        # Verificar si ya existe un registro con el mismo nombre
        if 'name' in vals:
            existing = self.search_count([('name', '=', vals['name'])])
            if existing > 0:
                raise UserError(_('Ya existe una nómina para %s. No se puede crear duplicados.') % vals['name'])
        return super(HR_Sueldos, self).create(vals)
    
    @api.model
    def default_get(self, fields):
        res = super(HR_Sueldos, self).default_get(fields)
        
        # Lista de meses en español
        meses_espanol = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        
        # Obtener el mes y año actual
        now = datetime.now()
        month_number = now.month
        month_name = meses_espanol[month_number - 1]
        year = now.year
        first_day = now.replace(day=1)
        last_day = (now.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        proposed_name = f"{month_name} {year}"
        
        # Verificar si ya existe una nómina para este mes/año
        existing = self.search_count([('name', '=', proposed_name)])
        if existing > 0:
            raise UserError(_('Ya existe una nómina para %s. No se puede crear duplicados.') % proposed_name)
        
        res['name'] = proposed_name
        
        # Resto del código para cargar empleados, préstamos, etc...
        employees = self.env['hr.employee'].search([])
        nomina_lines = []
        base_lines = []
        bonos_lines = []
        
        for emp in employees:
            licencia_dias = 0
            ausencias = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', 2),  # Licencias
                ('state', '=', 'validate'),
                ('date_from', '<=', last_day),
                ('date_to', '>=', first_day)
            ])
            
            for ausencia in ausencias:
                start_date = max(ausencia.date_from, first_day)
                end_date = min(ausencia.date_to, last_day)
                licencia_dias += (end_date - start_date).days + 1
            
            # Calcular horas de permisos (holiday_status_id = 5)
            permisos_horas = 0            
            permisos = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', 5),  # Permisos horas
                ('state', '=', 'validate'),
                ('date_from', '<=', last_day),
                ('date_to', '>=', first_day)
            ])
            
            for permiso in permisos:
                # Calcular horas del permiso que caen dentro del mes actual
                start_datetime = max(permiso.date_from, first_day)
                end_datetime = min(permiso.date_to, last_day)
                
                # Calcular diferencia en horas
                delta = end_datetime - start_datetime
                permisos_horas += delta.total_seconds() / 3600  # Convertir segundos a horas
            
            permisos_dias = 0
            permisos_d = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', 6),  # Permisos dias
                ('state', '=', 'validate'),
                ('date_from', '<=', last_day),
                ('date_to', '>=', first_day)
            ])

            for permiso in permisos_d:
                # Calcular dias del permiso que caen dentro del mes actual
                start_date = max(permiso.date_from, first_day)
                end_date = min(permiso.date_to, last_day)
                permisos_dias += (end_date - start_date).days + 1
                
            permisos_name = f"{permisos_dias} d / {permisos_horas} h"

            prestamo_valor = 0
            prestamos = self.env['hr.prestamo'].search([
                ('nombre', '=', emp.id),
                ('activo', '=', True),
                ('saldo', '>', 0)
            ])
            
            for prestamo in prestamos:
                if prestamo.saldo >= prestamo.cuota:
                    prestamo_valor += prestamo.cuota
                else:
                    prestamo_valor += prestamo.saldo
            
            nomina_lines.append((0, 0, {
                'empleado_id': emp.id,
                'rut': emp.identification_id,
                'dias_trabajados': 30 - licencia_dias - permisos_dias,
                'dias_ausentes': licencia_dias + permisos_dias,
                'licencia': licencia_dias,
                'comienzo': ausencias[0].date_from if ausencias else False,
                'permisos': permisos_name,  # Agregar las horas de permisos calculadas
                'prestamo': prestamo_valor,
            }))
            
            base_lines.append((0, 0, {
                'empleado_id': emp.id,
                'sueldo_base': emp.sueldo,
                'b_produccion': emp.bono_prod,
                'b_responsabilidad': emp.bono_resp,
                'b_resp_taller': emp.bono_resp_taller,  
                'comision': emp.bono_comi,       
                'b_puntualidad': emp.bono_punt,
                'b_asistencia': emp.bono_asist,
                'movilizacion': emp.bono_movil,
                'colacion': emp.bono_colac,
            }))

            bonos_lines.append((0, 0, {
                'empleado_id': emp.id,
                'b_est_trabajador': emp.bono_estud,
                'b_est_especial': emp.bono_estud_esp,
            }))
        
        res['nomina_id'] = nomina_lines
        res['nomina_id_base'] = base_lines
        res['nomina_id_bonos'] = bonos_lines
        return res

    def html_to_lines(self, html_content):
        """Convierte HTML a lista de líneas, manejando <br> y <p> como saltos de línea"""
        if not html_content:
            return []
        
        # Convertir <br>, <p> y </p> a marcadores de salto de línea
        text = html_content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        text = text.replace('<p>', '').replace('</p>', '\n')
        
        # Eliminar todas las demás etiquetas HTML
        text = re.sub(r'<[^>]+>', '', text)
        
        # Reemplazar entidades HTML comunes
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        # Dividir en líneas, eliminar vacías y espacios extras
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return lines if lines else ["Sin observaciones"]

    def export_to_excel(self):
        # Primero guardamos los cambios
        self.write({'fecha': fields.Date.today()})
        
        # Crear un libro de Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Nómina Consolidada')
        
        # Formato para encabezados
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D3D3D3',
            'border': 1
        })
        
        # Formato para datos
        data_format = workbook.add_format({
            'border': 1,
            'align': 'left'
        })
        
        # Formato para observaciones (texto con wrap y merge)
        obs_format = workbook.add_format({
            'text_wrap': True,
            'align': 'left',
            'valign': 'top',
            'border': 1
        })
        
        # Escribir encabezados
        headers = [
            'Empleado', 'RUT', 'Días Trabajados', 'Días Ausentes', 'Licencia (días)', 
            'Permisos', 'Préstamo', 'Pensión', 'Pedido Gas',
            'Sueldo Base', 'Bono Producción', 'Bono Responsabilidad',
            'Bono Taller', 'Comisión', 'Bono Puntualidad', 'Bono Asistencia',
            'Movilización', 'Colación', 'Bono Cumplimiento', 'Bono Estudios',
            'Bono Estudios Trabajador', 'Bono Estudios Especial', 'Bono Antigüedad',
            'Bono Vacaciones', 'Bono Terreno', 'Viático', 'Bono Día Trabajador',
            'Aguinaldo', 'Bono Productividad'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, len(header))  # Ajustar ancho de columna
        worksheet.set_column(0, 0, 40)  # Ajustar ancho de columna RUT
        worksheet.set_column(1, 1, 15)  # Ajustar ancho de columna RUT
        
        # Combinar datos de las tres secciones de nómina
        row = 1
        for sueldo in self:
            # Crear un diccionario para mapear empleado_id a sus datos
            empleados_data = {}
            
            # Procesar nomina_id (primera pestaña)
            for linea in sueldo.nomina_id:
                empleados_data[linea.empleado_id.id] = {
                    'empleado': linea.empleado_id.name,
                    'rut': linea.rut,
                    'dias_trabajados': linea.dias_trabajados,
                    'dias_ausentes': linea.dias_ausentes,
                    'licencia': linea.licencia,
                    'permisos': linea.permisos,
                    'prestamo': linea.prestamo,
                    'pension': linea.pension,
                    'pedido_gas': linea.pedido_gas
                }
            
            # Procesar nomina_id_base (segunda pestaña)
            for linea in sueldo.nomina_id_base:
                if linea.empleado_id.id in empleados_data:
                    empleados_data[linea.empleado_id.id].update({
                        'sueldo_base': linea.sueldo_base,
                        'b_produccion': linea.b_produccion,
                        'b_responsabilidad': linea.b_responsabilidad,
                        'b_resp_taller': linea.b_resp_taller,
                        'comision': linea.comision,
                        'b_puntualidad': linea.b_puntualidad,
                        'b_asistencia': linea.b_asistencia,
                        'movilizacion': linea.movilizacion,
                        'colacion': linea.colacion
                    })
            
            # Procesar nomina_id_bonos (tercera pestaña)
            for linea in sueldo.nomina_id_bonos:
                if linea.empleado_id.id in empleados_data:
                    empleados_data[linea.empleado_id.id].update({
                        'b_cumplimiento': linea.b_cumplimiento,
                        'b_estudio': linea.b_estudio,
                        'b_est_trabajador': linea.b_est_trabajador,
                        'b_est_especial': linea.b_est_especial,
                        'b_antiguedad': linea.b_antiguedad,
                        'b_vacaciones': linea.b_vacaciones,
                        'b_terreno': linea.b_terreno,
                        'viatico': linea.viatico,
                        'b_dia_trabajo': linea.b_dia_trabajo,
                        'aguinaldo': linea.aguinaldo,
                        'b_productividad': linea.b_productividad
                    })
            
            # Escribir datos en el Excel
            for emp_id, data in empleados_data.items():
                worksheet.write(row, 0, data.get('empleado', ''), data_format)
                worksheet.write(row, 1, data.get('rut', ''), data_format)
                worksheet.write(row, 2, data.get('dias_trabajados', 0), data_format)
                worksheet.write(row, 3, data.get('dias_ausentes', 0), data_format)
                worksheet.write(row, 4, data.get('licencia', 0), data_format)
                worksheet.write(row, 5, data.get('permisos', ''), data_format)
                worksheet.write(row, 6, data.get('prestamo', 0), data_format)
                worksheet.write(row, 7, data.get('pension', 0), data_format)
                worksheet.write(row, 8, data.get('pedido_gas', 0), data_format)
                worksheet.write(row, 9, data.get('sueldo_base', 0), data_format)
                worksheet.write(row, 10, data.get('b_produccion', 0), data_format)
                worksheet.write(row, 11, data.get('b_responsabilidad', 0), data_format)
                worksheet.write(row, 12, data.get('b_resp_taller', 0), data_format)
                worksheet.write(row, 13, data.get('comision', 0), data_format)
                worksheet.write(row, 14, data.get('b_puntualidad', 0), data_format)
                worksheet.write(row, 15, data.get('b_asistencia', 0), data_format)
                worksheet.write(row, 16, data.get('movilizacion', 0), data_format)
                worksheet.write(row, 17, data.get('colacion', 0), data_format)
                worksheet.write(row, 18, data.get('b_cumplimiento', 0), data_format)
                worksheet.write(row, 19, data.get('b_estudio', 0), data_format)
                worksheet.write(row, 20, data.get('b_est_trabajador', 0), data_format)
                worksheet.write(row, 21, data.get('b_est_especial', 0), data_format)
                worksheet.write(row, 22, data.get('b_antiguedad', 0), data_format)
                worksheet.write(row, 23, data.get('b_vacaciones', 0), data_format)
                worksheet.write(row, 24, data.get('b_terreno', 0), data_format)
                worksheet.write(row, 25, data.get('viatico', 0), data_format)
                worksheet.write(row, 26, data.get('b_dia_trabajo', 0), data_format)
                worksheet.write(row, 27, data.get('aguinaldo', 0), data_format)
                worksheet.write(row, 28, data.get('b_productividad', 0), data_format)
                row += 1
                
   
        # Procesar y escribir observaciones
        obs_lines = self.html_to_lines(sueldo.observaciones)
        if obs_lines:
            # Escribir título "OBSERVACIONES"
            worksheet.write(row + 2, 0, "OBSERVACIONES:", workbook.add_format({
                'bold': True,
                'border': 1,
                'align': 'left'
            }))
            
            # Escribir cada línea en filas consecutivas
            for i, line in enumerate(obs_lines):
                current_row = row + 3 + i
                
                # Combinar celdas para cada línea (de B a la última columna)
                worksheet.merge_range(
                    current_row, 1, current_row, len(headers) - 1,
                    line, workbook.add_format({
                        'text_wrap': True,
                        'align': 'left',
                        'valign': 'top',
                        'border': 1
                    })
                )      
                            # Escribir también en la columna A para mantener estructura
                worksheet.write(current_row, 0, "", workbook.add_format({'border': 1}))
                
                # Ajustar altura de fila según contenido
                worksheet.set_row(current_row, None, None, {'height': 20})

        workbook.close()
        output.seek(0)

        # Guardar el archivo en el registro
        file_name = f"Nomina_{sueldo.name.replace(' ', '_')}.xlsx"
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'file_name': file_name
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/hr.sueldos/{self.id}/excel_file/{file_name}?download=true',
            'target': 'self',
        }
    

class HR_Nomina(models.Model):
    _name = 'hr.nomina'
    _description = 'Nómina'

    sueldo_id = fields.Many2one('hr.sueldos', string='Sueldo', ondelete='cascade')
    sueldo_base_id = fields.Many2one('hr.sueldos', string='Sueldo Base', ondelete='cascade')
    sueldo_bonos_id = fields.Many2one('hr.sueldos', string='Sueldo Bonos', ondelete='cascade')
    
    mes = fields.Char(string='Mes', index=True)
    empleado_id = fields.Many2one('hr.employee', string='Nombre')
    rut = fields.Char(string='RUT')
    dias_trabajados = fields.Integer(string='Días trabajados', default=30)
    dias_ausentes = fields.Integer(string='Días ausentes', default=0)
    licencia = fields.Integer(string='Licencia', default=0)
    comienzo = fields.Date(string='Inicio de licencia')
    permisos = fields.Char(string='Permisos')
    prestamo = fields.Integer(string='Préstamo', default=0)
    pension = fields.Integer(string='Pensión alimenticia', default=0)
    pedido_gas = fields.Integer(string='Pedido de gas', default=0)

    sueldo_base = fields.Integer(string='Sueldo base', default=0)
    b_produccion = fields.Integer(string='Bono por producción', default=0)
    b_responsabilidad = fields.Integer(string='Bono por responsabilidad', default=0)
    b_resp_taller = fields.Integer(string='Bono por responsabilidad (taller)', default=0)
    comision = fields.Integer(string='Comisión taller', default=0)
    b_puntualidad = fields.Integer(string='Bono Puntualidad',default=0)
    b_asistencia = fields.Integer(string='Bono Asistencia',default=0)
    movilizacion = fields.Integer(string='Movilización', default=0)
    colacion = fields.Integer(string='Colación', default=0)

    b_cumplimiento = fields.Integer(string='Bono por cumplimiento', default=0)
    b_estudio = fields.Integer(string='Bono estudios anual', default=0)
    b_est_trabajador = fields.Integer(string='Bono de estudios (trabajador)', default=0)
    b_est_especial = fields.Integer(string='Bono de estudios (especial)', default=0)
    b_antiguedad = fields.Integer(string='Bono por antigüedad', default=0)
    b_vacaciones = fields.Integer(string='Bono por vacaciones', default=0)
    b_terreno = fields.Integer(string='Bono por trabajo en terreno', default=0)
    viatico = fields.Integer(string='Viático', default=0)
    b_dia_trabajo = fields.Integer(string='Bono por Día del Trabajador', default=0)
    aguinaldo = fields.Integer(string='Aguinaldo', default=0)
    b_productividad = fields.Integer(string='Bono por productividad', default=0)