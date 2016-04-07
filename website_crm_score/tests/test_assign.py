# -*- coding: utf-8 -*-
from openerp.addons.website_crm_score.tests.common import TestScoring
from openerp.tools import mute_logger


class test_assign(TestScoring):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_assign(self):
        cr, uid = self.cr, self.uid
        all_lead_ids = [self.lead0, self.lead1, self.lead2, self.lead3, self.lead4]

        count = self.crm_lead.search_count(cr, uid, [('id', 'in', all_lead_ids)], None)
        self.assertEqual(count, len(all_lead_ids), 'Some leads are missing for test %s vs %s' % (count, len(all_lead_ids)))
        # scoring
        self.website_crm_score.assign_scores_to_leads(cr, uid)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['score'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['score'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['score', 'active'], None)
        l3 = self.crm_lead.read(cr, uid, self.lead3, ['score', 'active'], dict(test_active=False))

        self.assertEqual(l0['score'], 1000, 'scoring failed')
        self.assertEqual(l1['score'], 900, 'scoring failed')
        self.assertEqual(l2['score'], 0, 'scoring failed')
        self.assertEqual(l3['score'], 900, 'scoring failed')
        self.assertEqual(l2['active'], True, ' should NOT be archived')
        self.assertEqual(l3['active'], False, ' should be archived')

        count = self.crm_lead.search_count(cr, uid, [('id', 'in', all_lead_ids)], None)
        self.assertEqual(count, len(all_lead_ids)-2, 'One lead should be deleted and one archived')

        # assignation
        self.team.direct_assign_leads(cr, uid, None)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['team_id', 'user_id'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['team_id', 'user_id'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['team_id', 'user_id'], None)

        self.assertEqual(l0['team_id'][0], self.team0, 'assignation failed')
        self.assertEqual(l1['team_id'][0], self.team1, 'assignation failed')
        self.assertEqual(l2['team_id'], False, 'assignation failed')

        self.assertEqual(l0['user_id'][0], self.salesmen0, 'assignation failed')
        self.assertEqual(l1['user_id'][0], self.salesmen1, 'assignation failed')
        self.assertEqual(l2['user_id'], False, 'assignation failed')
