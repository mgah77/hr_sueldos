from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class HR_Sueldos(models.Model):
    _name = 'hr.sueldos'
    _description = 'Pago de sueldos'

    name = fields.Char(string='Mes', index=True)
    nomina_id = fields.Many2one('hr.nomina', string='Nómina')
    fecha = fields.Date(string='Fecha', required=True)
    observaciones = fields.Text(string='Observaciones')

class HR_Nomina(models.Model):
    _name = 'hr.nomina'
    _description = 'Nómina'

    mes_pago = fields.One2many('hr.sueldos', 'nomina_id', string='Meses de pago')

    empleado_id = fields.Many2one('hr.employee', string='Nombre', required=True)
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
