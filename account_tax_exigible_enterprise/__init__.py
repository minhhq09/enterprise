# -*- coding: utf-8 -*-
import models

from openerp import SUPERUSER_ID

def _load_data(cr, registry):
    reports = [
        "l10n_ar_reports.account_financial_report_l10n_ar_tva0",
        "l10n_at_reports.account_financial_report_l10n_at_tva0",
        "l10n_au_reports.account_financial_report_l10n_au_gstrpt",
        "l10n_be_reports.account_financial_report_l10n_be_tva0",
        "l10n_bo_reports.account_financial_report_l10n_si",
        "l10n_br_reports.account_financial_report_l10n_br_tva0",
        "l10n_cl_reports.financial_report_l10n_cl",
        "l10n_co_reports.account_financial_report_l10n_co",
        "l10n_de_skr03_reports.financial_report_l10n_de_skr03",
        "l10n_de_skr04_reports.financial_report_l10n_de",
        "l10n_do_reports.account_financial_report_l10n_do",
        "l10n_es_reports.financial_report_l10n_es",
        "l10n_et_reports.account_financial_report_l10n_et",
        "l10n_fr_reports.account_financial_report_l10n_fr",
        "l10n_gr_reports.account_financial_report_l10n_si",
        "l10n_hr_reports.financial_report_l10n_hr_report",
        "l10n_in_reports.account_financial_report_l10n_in_report",
        "l10n_jp_reports.account_financial_report_l10n_jp",
        "l10n_lu_reports.account_financial_report_l10n_lu",
        "l10n_ma_reports.account_financial_report_l10n_ma_report",
        "l10n_nl_reports.financial_report_l10n_nl",
        "l10n_no_reports.financial_report_l10n_no",
        "l10n_pl_reports.account_financial_report_l10n_pl",
        "l10n_ro_reports.account_financial_report_l10n_ro",
        "l10n_sg_reports.account_financial_report_l10n_sg",
        "l10n_si_reports.financial_report_l10n_si",
        "l10n_th_reports.account_financial_report_l10n_th",
        "l10n_uk_reports.financial_report_l10n_uk",
        "l10n_uy_reports.financial_report_l10n_uy",
        "l10n_vn_reports.account_financial_report_l10n_vn",
    ]
    for report in reports:
        res = registry['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, report)
        if res:
            res.tax_report = 1
    return
