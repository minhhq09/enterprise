# -*- coding: utf-8 -*-
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from math import floor
from openerp import http, _
from openerp.http import request
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from stat_types import STAT_TYPES, FORECAST_STAT_TYPES, compute_mrr_growth_values

# We need to use the same formatting as the one in read_group (see models.py)
DISPLAY_FORMATS = {
    'day': '%d %b %Y',
    'week': 'W%W %Y',
    'week_special': '%w W%W %Y',
    'month': '%B %Y',
}


class RevenueKPIsDashboard(http.Controller):

    @http.route('/account_contract_dashboard/fetch_cohort_report', type='json', auth='user')
    def cohort(self, date_start, cohort_period, cohort_interest, contract_template_ids=None, company_ids=None):
        """
        Get a Cohort Analysis report

        :param date_start: date of the first contract to take into account
        :param cohort_period: cohort period. Between 'day','week','month'
        :param cohort_interest: cohort interest. Could be 'value' or 'number'
        :param contract_template_ids: filtering on specific contract templates
        :param company_ids: filtering on specific companies
        """
        cohort_report = []
        company_currency_id = request.env.user.company_id.currency_id

        subs_fields = ['date_start', 'recurring_total']
        subs_domain = [
            ('type', '=', 'contract'),
            ('date_start', '>=', date_start),
            ('date_start', '<', date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))]
        if contract_template_ids:
            subs_domain.append(('template_id', 'in', contract_template_ids))
        if company_ids:
            subs_domain.append(('company_id', 'in', company_ids))

        for cohort_group in request.env['sale.subscription'].read_group(domain=subs_domain, fields=['date_start'], groupby='date_start:' + cohort_period):
            tf = cohort_group['date_start:' + cohort_period]
            cohort_subs = request.env['sale.subscription'].search(cohort_group['__domain'])
            cohort_date = datetime.strptime(tf, DISPLAY_FORMATS[cohort_period])
            if cohort_period == 'week':
                # When used with the strptime() method, %W is only used in calculations when the day of the week and the year are specified.
                # See https://docs.python.org/2/library/datetime.html
                # We need to use 1 (Monday) because %W consider Monday as the first day of the week
                cohort_date = datetime.strptime('1 ' + tf, DISPLAY_FORMATS['week_special'])

            if cohort_interest == 'value':
                starting_value = float(sum([x.currency_id.compute(x.recurring_total, company_currency_id) if x.currency_id else x.recurring_total for x in cohort_subs]))
            else:
                starting_value = float(len(cohort_subs))
            cohort_line = []
            cohort_line.append({
                'value': starting_value,
                'percentage': 100,
                'domain': cohort_group['__domain'],
            })

            for ij in range(1, 16):
                ij_start_date = cohort_date
                if cohort_period == 'day':
                    ij_start_date += relativedelta(days=ij)
                    ij_end_date = ij_start_date + relativedelta(days=1)
                elif cohort_period == 'week':
                    ij_start_date += relativedelta(days=7*ij)
                    ij_end_date = ij_start_date + relativedelta(days=7)
                else:
                    ij_start_date += relativedelta(months=ij)
                    ij_end_date = ij_start_date + relativedelta(months=1)

                if ij_start_date > datetime.today():
                    # Who can predict the future, right ?
                    cohort_line.append({
                        'value': '-',
                        'percentage': '-',
                        'domain': '',
                    })
                    continue

                significative_period = ij_start_date.strftime(DISPLAY_FORMATS[cohort_period])
                churned_subs = [x for x in cohort_subs if x.date and datetime.strptime(x.date, DEFAULT_SERVER_DATE_FORMAT).strftime(DISPLAY_FORMATS[cohort_period]) == significative_period]

                if cohort_interest == 'value':
                    churned_value = sum([x.currency_id.compute(x.recurring_total, company_currency_id) if x.currency_id else x.recurring_total for x in churned_subs])
                else:
                    churned_value = len(churned_subs)

                cohort_remaining = cohort_line[-1]['value'] - churned_value
                cohort_line_ij = {
                    'value': cohort_remaining,
                    'percentage': starting_value and round(100*(cohort_remaining)/starting_value, 1) or 0,
                    'domain': cohort_group['__domain'] + [
                        ("date", ">=", ij_start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                        ("date", "<", ij_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT))]
                }
                cohort_line.append(cohort_line_ij)

            cohort_report.append({
                'period': tf,
                'values': cohort_line,
            })

        return {
            'contract_templates': request.env['sale.subscription'].search_read([('state', '=', 'open'), ('type', '=', 'template')], ['name']),
            'companies': request.env['res.company'].search_read([], ['name']),
            'cohort_report': cohort_report,
            'currency_id': company_currency_id.id,
        }

    @http.route('/account_contract_dashboard/fetch_data', type='json', auth='user')
    def fetch_data(self):
        # context is necessary so _(...) can translate in the appropriate language
        context = request.env.context
        return {
            'stat_types': {
                key: {
                    'name': _(stat['name']),
                    'dir': stat['dir'],
                    'code': stat['code'],
                    'prior': stat['prior'],
                    'add_symbol': stat['add_symbol'],
                }
                for key, stat in STAT_TYPES.iteritems()
            },
            'forecast_stat_types': {
                key: {
                    'name': _(stat['name']),
                    'code': stat['code'],
                    'prior': stat['prior'],
                    'add_symbol': stat['add_symbol'],
                }
                for key, stat in FORECAST_STAT_TYPES.iteritems()
            },
            'currency_id': request.env.user.company_id.currency_id.id,
            'contract_templates': request.env['sale.subscription'].search_read([('type', '=', 'template'), ('state', '=', 'open')], fields=['name']),
            'companies': request.env['res.company'].search_read([], fields=['name']),
            'show_demo': request.env['account.invoice.line'].search_count([('asset_start_date', '!=', False)]) == 0,
        }

    @http.route('/account_contract_dashboard/companies_check', type='json', auth='user')
    def companies_check(self, company_ids):
        company_ids = request.env['res.company'].browse(company_ids)
        currency_ids = company_ids.mapped('currency_id')

        if len(currency_ids) == 1:
            return {
                'result': True,
                'currency_id': currency_ids.id,
            }
        elif len(company_ids) == 0:
            message = _('No company selected.')
        elif len(currency_ids) >= 1:
            message = _('It makes no sense to sum MRR of different currencies. Please select companies with the same currency.')
        else:
            message = _('Unknown error')

        return {
            'result': False,
            'error_message': message,
        }

    @http.route('/account_contract_dashboard/get_default_values_forecast', type='json', auth='user')
    def get_default_values_forecast(self, forecast_type, end_date=None, contract_ids=None, company_ids=None):

        if not end_date:
            end_date = date.today()
        else:
            end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)

        net_new_mrr = compute_mrr_growth_values(end_date, end_date, contract_ids=contract_ids, company_ids=company_ids)['net_new_mrr']
        revenue_churn = self.compute_stat('revenue_churn', end_date, end_date, contract_ids=contract_ids, company_ids=company_ids)

        result = {
            'expon_growth': 15,
            'churn': revenue_churn,
            'projection_time': 12,
        }

        if 'mrr' in forecast_type:
            mrr = self.compute_stat('mrr', end_date, end_date, contract_ids=contract_ids, company_ids=company_ids)

            result['starting_value'] = mrr
            result['linear_growth'] = net_new_mrr
        else:
            arpu = self.compute_stat('arpu', end_date, end_date, contract_ids=contract_ids, company_ids=company_ids)
            nb_contracts = self.compute_stat('nb_contracts', end_date, end_date, contract_ids=contract_ids, company_ids=company_ids)

            result['starting_value'] = nb_contracts
            result['linear_growth'] = 0 if arpu == 0 else net_new_mrr/arpu
        return result

    @http.route('/account_contract_dashboard/get_stats_history', type='json', auth='user')
    def get_stats_history(self, stat_type, start_date, end_date, contract_ids=None, company_ids=None):

        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)

        results = {}

        for delta in [1, 3, 12]:
            results['value_' + str(delta) + '_months_ago'] = self.compute_stat(
                stat_type,
                start_date - relativedelta(months=+delta),
                end_date - relativedelta(months=+delta),
                contract_ids=contract_ids,
                company_ids=company_ids)

        return results

    @http.route('/account_contract_dashboard/get_stats_by_plan', type='json', auth='user')
    def get_stats_by_plan(self, stat_type, start_date, end_date, contract_ids=None, company_ids=None):

        results = []

        domain = [('type', '=', 'template'), ('state', '=', 'open')]
        if contract_ids:
            domain += [('id', 'in', contract_ids)]

        contract_ids = request.env['sale.subscription'].search(domain)

        for contract in contract_ids:
            sale_subscriptions = request.env['sale.subscription'].search([('template_id', '=', contract.id)])
            analytic_account_ids = [sub.analytic_account_id.id for sub in sale_subscriptions]

            lines_domain = [
                ('asset_start_date', '<=', end_date),
                ('asset_end_date', '>=', end_date),
                ('account_analytic_id', 'in', analytic_account_ids),
            ]
            if company_ids:
                lines_domain.append(('company_id', 'in', company_ids))
            recurring_invoice_line_ids = request.env['account.invoice.line'].search(lines_domain)
            value = self.compute_stat(stat_type, start_date, end_date, contract_ids=[contract.id])
            results.append({
                'name': contract.name,
                'nb_customers': len(recurring_invoice_line_ids.mapped('account_analytic_id')),
                'value': value,
            })

        results = sorted((results), key=lambda k: k['value'], reverse=True)

        return results

    @http.route('/account_contract_dashboard/compute_graph_mrr_growth', type='json', auth='user')
    def compute_graph_mrr_growth(self, start_date, end_date, contract_ids=None, company_ids=None, points_limit=0):

        # By default, points_limit = 0 mean every points

        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
        delta = end_date - start_date

        ticks = self._get_pruned_tick_values(range(delta.days + 1), points_limit)

        results = defaultdict(list)

        # This is rolling month calculation
        for i in ticks:
            date = start_date + timedelta(days=i)
            date_splitted = str(date).split(' ')[0]

            computed_values = compute_mrr_growth_values(date, date, contract_ids=contract_ids, company_ids=company_ids)

            for k in ['new_mrr', 'churned_mrr', 'expansion_mrr', 'down_mrr', 'net_new_mrr']:
                results[k].append({
                    '0': date_splitted,
                    '1': computed_values[k]
                })

        return results

    @http.route('/account_contract_dashboard/compute_graph_and_stats', type='json', auth='user')
    def compute_graph_and_stats(self, stat_type, start_date, end_date, contract_ids=None, company_ids=None, points_limit=30):
        """ Returns both the graph and the stats"""

        # This avoids to make 2 RPCs instead of one
        graph = self.compute_graph(stat_type, start_date, end_date, contract_ids=contract_ids, company_ids=company_ids, points_limit=points_limit)
        stats = self._compute_stat_trend(stat_type, start_date, end_date, contract_ids=contract_ids, company_ids=company_ids)

        return {
            'graph': graph,
            'stats': stats,
        }

    @http.route('/account_contract_dashboard/compute_graph', type='json', auth='user')
    def compute_graph(self, stat_type, start_date, end_date, contract_ids=None, company_ids=None, points_limit=30):

        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
        delta = end_date - start_date

        ticks = self._get_pruned_tick_values(range(delta.days + 1), points_limit)

        results = []
        for i in ticks:
            # METHOD NON-OPTIMIZED (could optimize it using SQL with generate_series)
            date = start_date + timedelta(days=i)
            value = self.compute_stat(stat_type, date, date, contract_ids=contract_ids, company_ids=company_ids)

            # '0' and '1' are the keys for nvd3 to render the graph
            results.append({
                '0': str(date).split(' ')[0],
                '1': value,
            })

        return results

    def _compute_stat_trend(self, stat_type, start_date, end_date, contract_ids=None, company_ids=None):

        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)
        start_date_delta = start_date - relativedelta(months=+1)
        end_date_delta = end_date - relativedelta(months=+1)

        value_1 = self.compute_stat(stat_type, start_date_delta, end_date_delta, contract_ids=contract_ids, company_ids=company_ids)
        value_2 = self.compute_stat(stat_type, start_date, end_date, contract_ids=contract_ids, company_ids=company_ids)

        perc = 0 if value_1 == 0 else round(100*(value_2 - value_1)/float(value_1), 1)

        result = {
            'value_1': str(value_1),
            'value_2': str(value_2),
            'perc': perc,
        }
        return result

    @http.route('/account_contract_dashboard/compute_stat', type='json', auth='user')
    def compute_stat(self, stat_type, start_date, end_date, contract_ids=None, company_ids=None):

        if isinstance(start_date, (str, unicode)):
            start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        if isinstance(end_date, (str, unicode)):
            end_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT)

        return STAT_TYPES[stat_type]['compute'](start_date, end_date, contract_ids=contract_ids, company_ids=company_ids)

    def _get_pruned_tick_values(self, ticks, nb_desired_ticks):
        if nb_desired_ticks == 0:
            return ticks

        nb_values = len(ticks)
        keep_one_of = max(1, floor(nb_values / float(nb_desired_ticks)))

        ticks = [x for x in ticks if x % keep_one_of == 0]

        return ticks
