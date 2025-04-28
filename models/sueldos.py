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
                ('holiday_status_id', '=', 5),  # Permisos
                ('state', '=', 'validate'),
                ('date_from', '<=', last_day),
                ('date_to', '>=', first_day)
            ])
            
            for permiso in permisos:
                # Calcular horas del permiso que caen dentro del mes actual
                start_datetime = max(permiso.date_from, fields.Datetime.to_datetime(first_day))
                end_datetime = min(permiso.date_to, fields.Datetime.to_datetime(last_day))
                
                # Calcular diferencia en horas
                delta = end_datetime - start_datetime
                permisos_horas += delta.total_seconds() / 3600  # Convertir segundos a horas
            
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
                'dias_trabajados': 30 - licencia_dias,
                'dias_ausentes': licencia_dias,
                'licencia': licencia_dias,
                'comienzo': ausencias[0].date_from if ausencias else False,
                'permisos': permisos_horas,  # Agregar las horas de permisos calculadas
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

class HR_Nomina(models.Model):
    _name = 'hr.nomina'
    _description = 'Nómina'

    sueldo_id = fields.Many2one('hr.sueldos', string='Sueldo', ondelete='cascade')
    sueldo_base_id = fields.Many2one('hr.sueldos', string='Sueldo Base', ondelete='cascade')
    sueldo_bonos_id = fields.Many2one('hr.sueldos', string='Sueldo Bonos', ondelete='cascade')
    
    mes = fields.Char(string='Mes', index=True)
    empleado_id = fields.Many2one('hr.employee', string='Nombre')
    dias_trabajados = fields.Integer(string='Días trabajados', default=30)
    dias_ausentes = fields.Integer(string='Días ausentes', default=0)
    licencia = fields.Integer(string='Licencia', default=0)
    comienzo = fields.Date(string='Inicio de licencia')
    permisos = fields.Integer(string='Permisos', default=0)
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