# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{ 'name': 'HR Sueldos',
'summary': "Pago Sueldos",
'author': "Mauricio Gah",
'license': "AGPL-3",
'application': "True",
'version': "1.0",
'data': ['security/ir.model.access.csv',     
         'views/menu.xml',
         'views/sueldos.xml',
        
],

'depends': ['base' , 'contacts' , 'hr' , 'parches', 'hr_prestamo'],
'external_dependencies': {
    'python': ['xlsxwriter'],
},
'installable': True,
'application': True,
}
