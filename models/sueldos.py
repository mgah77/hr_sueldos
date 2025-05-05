from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime , timedelta

class HR_Sueldos(models.Model):
    _name = 'hr.sueldos'
    _description = 'Pago de sueldos'
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Ya existe una nómina con este mes/año. No se puede crear duplicados.'),
    ]

    name = fields.Char(string='Mes', index=True)
    nomina_id = fields.One2many('hr.nomina', 'sueldo_id', string='Nómina')
    nomina_id_base = fields.One2many('hr.nomina', 'sueldo_base_id', string='Nómina')
    nomina_id_bonos = fields.One2many('hr.nomina', 'sueldo_bonos_id', string='Nómina de bonos')
    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    observaciones = fields.Text(string='Observaciones')
    
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

        def exportar_a_excel(self):
        # Obtener los datos filtrados
        ultimo_dia_mes = calendar.monthrange(self.anno, int(self.mes))[1]
        nomina = self.env['hr.sueldos'].search([
            ('name', '=', self.name)
        ])

        # Obtener las descripciones de los servicios
        #nomina_model = self.env['elihel.servicio']
        #tipo_servicio_selection = dict(servicio_model._fields['tipo_servicio'].selection)

        # Crear un libro de Excel y una hoja
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Nomina Mes')

        # Definir los encabezados fijos
        headers_fijos = [
            'Certificado', 'Barco', 'Matrícula', 'Fecha', 'Camiones'
        ]

        # Obtener todos los servicios únicos con sus descripciones
        servicios_unicos = set()
        for trabajo in trabajos:
            for camion in trabajo.camion_ids:
                for servicio in camion.servicio_ids:
                    descripcion_servicio = tipo_servicio_selection.get(servicio.tipo_servicio, servicio.tipo_servicio)
                    servicios_unicos.add(descripcion_servicio)

        # Convertir el conjunto de servicios únicos a una lista ordenada
        servicios_unicos = sorted(list(servicios_unicos))

        # Escribir los encabezados fijos
        for col, header in enumerate(headers_fijos):
            sheet.write(0, col, header)

        # Escribir los encabezados de servicios
        for col, servicio in enumerate(servicios_unicos, start=len(headers_fijos)):
            sheet.write(0, col, servicio)

        # Escribir los datos
        row = 1
        for trabajo in trabajos:
            primera_fila_trabajo = True  # Bandera para la primera fila del trabajo
            for camion in trabajo.camion_ids:
                # Formatear la fecha en formato dd-mmm-YY
                fecha_formateada = trabajo.fecha_llegada.strftime('%d-%b-%y')

                # Escribir los datos fijos solo en la primera fila del trabajo
                if primera_fila_trabajo:
                    sheet.write(row, 0, trabajo.numero_certificado)
                    sheet.write(row, 1, trabajo.nombre)
                    sheet.write(row, 2, trabajo.matricula)
                    sheet.write(row, 3, fecha_formateada)
                    primera_fila_trabajo = False
                else:
                    # Dejar vacías las celdas de Certificado, Barco, Matrícula y Fecha
                    sheet.write(row, 0, "")
                    sheet.write(row, 1, "")
                    sheet.write(row, 2, "")
                    sheet.write(row, 3, "")

                # Escribir los datos del camión
                sheet.write(row, 4, camion.matricula)

                # Contar los servicios por tipo para este camión
                servicios_camion = {}
                for servicio in camion.servicio_ids:
                    descripcion_servicio = tipo_servicio_selection.get(servicio.tipo_servicio, servicio.tipo_servicio)
                    if descripcion_servicio in servicios_camion:
                        servicios_camion[descripcion_servicio] += servicio.cantidad
                    else:
                        servicios_camion[descripcion_servicio] = servicio.cantidad

                # Escribir la cantidad de servicios por tipo
                for col, servicio in enumerate(servicios_unicos, start=len(headers_fijos)):
                    cantidad = servicios_camion.get(servicio, 0)
                    sheet.write(row, col, cantidad)

                row += 1

        # Guardar el archivo en un objeto BytesIO
        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        # Codificar el archivo en base64
        excel_file = base64.b64encode(output.read())
        output.close()

        # Crear un registro de ir.attachment para descargar el archivo
        attachment = self.env['ir.attachment'].create({
            'name': f"Informe_Trabajos_{self.lugar}_{self.mes}_{self.anno}.xls",
            'datas': excel_file,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
        })

        # Devolver una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=true",
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
    dias_trabajados = fields.Integer(string='Días trabajados', default=30)
    dias_ausentes = fields.Integer(string='Días ausentes')
    licencia = fields.Integer(string='Licencia')
    comienzo = fields.Date(string='Inicio de licencia')
    permisos = fields.Char(string='Permisos')
    prestamo = fields.Integer(string='Préstamo')
    pension = fields.Integer(string='Pensión alimenticia')
    pedido_gas = fields.Integer(string='Pedido de gas')

    sueldo_base = fields.Integer(string='Sueldo base')
    b_produccion = fields.Integer(string='Bono por producción')
    b_responsabilidad = fields.Integer(string='Bono por responsabilidad')
    b_resp_taller = fields.Integer(string='Bono por responsabilidad (taller)')
    comision = fields.Integer(string='Comisión taller')
    b_puntualidad = fields.Integer(string='Bono Puntualidad')
    b_asistencia = fields.Integer(string='Bono Asistencia')
    movilizacion = fields.Integer(string='Movilización')
    colacion = fields.Integer(string='Colación')

    b_cumplimiento = fields.Integer(string='Bono por cumplimiento')
    b_estudio = fields.Integer(string='Bono estudios anual')
    b_est_trabajador = fields.Integer(string='Bono de estudios (trabajador)')
    b_est_especial = fields.Integer(string='Bono de estudios (especial))
    b_antiguedad = fields.Integer(string='Bono por antigüedad')
    b_vacaciones = fields.Integer(string='Bono por vacaciones')
    b_terreno = fields.Integer(string='Bono por trabajo en terreno')
    viatico = fields.Integer(string='Viático')
    b_dia_trabajo = fields.Integer(string='Bono por Día del Trabajador')
    aguinaldo = fields.Integer(string='Aguinaldo')
    b_productividad = fields.Integer(string='Bono por productividad')