#!/bin/sh

barcode -t 2x7+40+40 -m 50x30 -p A4 -e code128b -o barcodes_demo_data.ps <<BARCODES
9873031254663
9789878466514
1312465423164
6548978946196
5478592110363
7845854641328
8798465112398
LOT-000003
LOT-000004
LOT-000005
LOT-000006
MO/00001
MO/00002
MO/00003
BARCODES

barcode -t 2x6+20+40 -m 30x30 -m 30x30 -p A4 -e code128b -o production_barcodes_actions.ps <<BARCODES
O-BTN.action_assign
O-BTN.button_unreserve
O-BTN.button_plan
O-BTN.button_unplan
O-BTN.open_produce_product
O-BTN.do_produce
O-BTN.post_inventory
O-BTN.button_mark_done
O-BTN.button_scrap
O-BTN.action_cancel
O-CMD.SAVE
BARCODES

barcode -t 2x6+20+40 -m 30x30 -p A4 -e code128b -o workorder_barcodes_actions.ps <<BARCODES
O-BTN.button_start
O-BTN.button_pending
O-BTN.record_production
O-BTN.button_scrap
O-BTN.button_finish
O-BTN.button_unblock
BARCODES


# add title in postscript :
#
# /showTitle % stack: str x y
# {
#   /Helvetica findfont 12 scalefont setfont
#   moveto show
# } def
#
# e.g (My Product) 81.65 810 showTitle
