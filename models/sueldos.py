from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class HR_Sueldos(models.Model):
    _name = 'hr.sueldos'
    _description = 'Pago de sueldos'

    name = fields.Char(string='Mes', index=True)
    nomina_id = fields.One2many('hr.nomina', 'sueldo_id', string='Nómina')
    nomina_id_bonos = fields.One2many('hr.nomina', 'sueldo_bonos_id', string='Nómina de bonos')
    fecha = fields.Date(string='Fecha', required=True, default=fields.Date.today)
    observaciones = fields.Text(string='Observaciones')
    
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
        
        res['name'] = f"{month_name} {year}"
        
        # Obtener todos los empleados activos
        employees = self.env['hr.employee'].search([])
        # Crear líneas de nómina para cada empleado (sin guardar)
        nomina_lines = []
        bonos_lines = []
        for emp in employees:
            nomina_lines.append((0, 0, {
                'empleado_id': emp.id,
                'dias_trabajados': 30,
                'dias_ausentes': 0,
                # otros campos por defecto...
            }))
            bonos_lines.append((0, 0, {
                'empleado_id': emp.id,
                'b_estudio': emp.bono_estud,  # Cargar el bono de estudios del empleado
                'b_est_trabajador': emp.bono_estud_esp,  # También cargar el bono especial si lo necesitas
                # otros campos por defecto...
            }))
        res['nomina_id'] = nomina_lines
        res['nomina_id_bonos'] = bonos_lines  # Líneas con los bonos cargados
        return res

class HR_Nomina(models.Model):
    _name = 'hr.nomina'
    _description = 'Nómina'

    sueldo_id = fields.Many2one('hr.sueldos', string='Sueldo')
    sueldo_bonos_id = fields.Many2one('hr.sueldos', string='Sueldo Bonos')
    
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

    b_cumplimiento = fields.Integer(string='Bono por cumplimiento', default=0)
    b_estudio = fields.Integer(string='Bono por estudios', default=0)
    b_est_trabajador = fields.Integer(string='Bono de estudios (trabajador)', default=0)
    b_antiguedad = fields.Integer(string='Bono por antigüedad', default=0)
    b_vacaciones = fields.Integer(string='Bono por vacaciones', default=0)
    b_terreno = fields.Integer(string='Bono por trabajo en terreno', default=0)
    viatico = fields.Integer(string='Viático', default=0)
    b_dia_trabajo = fields.Integer(string='Bono por Día del Trabajador', default=0)
    aguinaldo = fields.Integer(string='Aguinaldo', default=0)
    b_productividad = fields.Integer(string='Bono por productividad', default=0)