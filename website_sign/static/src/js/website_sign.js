
(function() {
    'use strict';

    var qweb = openerp.qweb;
    var ajax = openerp;
    var Widget = openerp.Widget;
    var Class = openerp.Class;
    var website = openerp.website;

    var CLASSES = {}, WIDGETS = {};

    var websiteSign = null;

    /* -------------------------------------------------- */
    /*  WebsiteSign Class (set of some useful functions)  */
    /* -------------------------------------------------- */
    CLASSES.WebsiteSign = Class.extend({
        init: function() {
            this.currentRole = $('.o_sign_parties_input_info').first().data('id');
            this.types = {};
        },

        getPartnerSelectConfiguration: function() {
            var self = this;

            if(self.getPartnerSelectConfiguration.def === undefined) {
                self.getPartnerSelectConfiguration.def = new $.Deferred();

                var select2Options = {
                    allowClear: true,

                    formatResult: function(data, resultElem, searchObj) {
                        var partner = $.parseJSON(data.text);
                        if($.isEmptyObject(partner)) {
                            var partnerInfo = self.partnerRegexMatch(searchObj.term);
                            var $elem = $(data.element[0]);
                            if(!partnerInfo) {
                                $elem.removeData('name mail');
                                return "Create: \"" + searchObj.term + "\" <span class='fa fa-exclamation-circle' style='color:rgb(255, 192, 128);'/> <span style='font-size:0.7em'>Enter mail (and name if you want)</span>";
                            }

                            $elem.data(partnerInfo);
                            return "Create: \"" + $elem.data('name') + " (" + $elem.data('mail') + ")" + "\" <span class='fa fa-check-circle' style='color:rgb(128, 255, 128);'/>";
                        }

                        return $("<div/>", {html: ((partner['new'])? "New: " : "") + partner.name + " (" + partner.email + ")"}).css('border-bottom', '1px dashed silver');
                    },

                    formatSelection: function(data) {
                        var partner = $.parseJSON(data.text);
                        if($.isEmptyObject(partner))
                            return "Error";

                        return ((partner['new'])? "New: " : "") + partner.name + " (" + partner.email + ")";
                    },

                    matcher: function(search, data) {
                        var partner = $.parseJSON(data);
                        if($.isEmptyObject(partner))
                            return (search.length > 0);

                        var searches = search.toUpperCase().split(/[ ()]/);
                        for(var i = 0 ; i < searches.length ; i++) {
                            if(partner['email'].toUpperCase().indexOf(searches[i]) < 0 && partner['name'].toUpperCase().indexOf(searches[i]) < 0)
                                return false;
                        }
                        return true;
                    }
                };

                var selectChangeHandler = function(e) {
                    if(e.added && e.added.element.length > 0) {
                        var $option = $(e.added.element[0]);
                        var $select = $option.parent();
                        if(parseInt($option.val()) !== 0)
                            return true;

                        setTimeout(function() {
                            $select.select2("destroy");

                            if(!$option.data('mail'))
                                $option.prop('selected', false);
                            else {
                                if(!$select.data('newNumber'))
                                    $select.data('newNumber', 0);
                                var newNumber = $select.data('newNumber') - 1;
                                $select.data('newNumber', newNumber);

                                $option.val(newNumber);
                                $option.html('{"name": "' + $option.data('name') + '", "email": "' + $option.data('mail') + '", "new": "1"}');

                                var $newOption = $('<option/>', {
                                    value: 0,
                                    html: "{}"
                                });
                                $select.find('option').filter(':last').after($newOption);
                            }

                            $select.select2(select2Options);
                        }, 0);
                    }
                    else if(e.removed && e.removed.element.length > 0) {
                        var $option = $(e.removed.element[0]);
                        var $select = $option.parent();
                        if(parseInt($option.val()) >= 0)
                            return true;

                        setTimeout(function() {
                            $select.select2("destroy");
                            $select.find('option[value=' + $option.val() + ']').remove();
                            $select.select2(select2Options);
                        }, 0);
                    }
                };

                return ajax.jsonRpc("/sign/get_partners", 'call', {}).then(function(data) {
                    var $partnerSelect = $('<select><option/></select>');
                    for(var i = 0 ; i < data.length ; i++)
                        $partnerSelect.append($('<option/>', {
                            value: data[i]['id'],
                            html: JSON.stringify(data[i])
                        }));
                    $partnerSelect.append($('<option/>', {
                        value: 0,
                        html: "{}"
                    }));

                    return self.getPartnerSelectConfiguration.def.resolve($partnerSelect.html(), select2Options, selectChangeHandler).promise();
                });
            }

            return self.getPartnerSelectConfiguration.def.promise();
        },

        setAsPartnerSelect: function($select) {
            return this.getPartnerSelectConfiguration().then(function(selectHTML, select2Options, selectChangeHandler) {
                $select.select2('destroy');
                $select.html(selectHTML).css('width', '100%').addClass('form-control');
                $select.select2(select2Options);
                $select.off('change').on('change', selectChangeHandler);
            });
        },

        partnerRegexMatch: function(str) {
            var partnerInfo = str.match(/(?:\s|\()*(((?:\w|-|\.)+)@(?:\w|-)+\.(?:\w|-)+)(?:\s|\))*/);
            if(!partnerInfo || partnerInfo[1] === undefined)
                return false;
            else {
                var index = str.indexOf(partnerInfo[0]);
                var name = str.substr(0, index) + " " + str.substr(index+partnerInfo[0].length);
                if(name === " ")
                    name = partnerInfo[2];

                return {'name': name, 'mail': partnerInfo[1]};
            }
        },

        processPartnersSelectionThen: function($select, thenFunction) {
            var partnerIDs = $select.val();
            if(!partnerIDs || partnerIDs.length <= 0)
                return false;

            if(typeof partnerIDs === 'string')
                partnerIDs = [parseInt(partnerIDs)];

            var partners = [];
            var waitForPartnerCreations = [];
            $(partnerIDs).each(function(i, partnerID) {
                partnerID = parseInt(partnerID);
                if(partnerID < 0) {
                    var partnerInfo = $.parseJSON($select.find('option[value=' + partnerID + ']').html());
                    waitForPartnerCreations.push(ajax.jsonRpc("/sign/new_partner", 'call', {
                        'name': partnerInfo.name.trim(),
                        'mail': partnerInfo.email.trim()
                    }).then(function(pID) {
                        partners.push(pID);
                    }));
                }
                else if(partnerID === 0)
                    return;
                else
                    partners.push(partnerID);
            });

            return $.when.apply($, waitForPartnerCreations).then(function() {
                thenFunction(partners);
            });
        },

        getResponsibleSelectConfiguration: function() {
            var self = this;

            if(self.getResponsibleSelectConfiguration.def === undefined) {
                self.getResponsibleSelectConfiguration.def = new $.Deferred();

                var select2Options = {
                    placeholder: "Select the responsible",
                    allowClear: false,

                    formatResult: function(data, resultElem, searchObj) {
                        if(!data.text) {
                            $(data.element[0]).data('create_name', searchObj.term);
                            return "Create: \"" + searchObj.term + "\"";
                        }
                        return data.text;
                    },

                    formatSelection: function(data) {
                        if(!data.text)
                            return $(data.element[0]).data('create_name');
                        return data.text;
                    },

                    matcher: function(search, data) {
                        if(!data)
                            return (search.length > 0);
                        return (data.toUpperCase().indexOf(search.toUpperCase()) > -1);
                    }
                };

                var selectChangeHandler = function(e) {
                    var $select = $(e.target), $option = $(e.added.element[0]);

                    var resp = parseInt($option.val());
                    var name = $option.html() || $option.data('create_name');
                    
                    if(resp >= 0 || !name)
                        return false;

                    ajax.jsonRpc("/sign/add_signature_item_party", 'call', {
                        'name': name
                    }).then(function(partyID) {
                        var $newResponsibleOption = $('<input type="hidden"/>');
                        $newResponsibleOption.data({id: partyID, name: name}).addClass('o_sign_parties_input_info');
                        $('.o_sign_parties_input_info').filter(':last').after($newResponsibleOption);

                        self.getResponsibleSelectConfiguration.def = undefined;
                        self.setAsResponsibleSelect($select, partyID);
                    });
                };

                var $responsibleSelect = $('<select><option/></select>');
                $('.o_sign_parties_input_info').each(function(i, el) {
                    $responsibleSelect.append($('<option/>', {
                        value: parseInt($(el).data('id')),
                        html: $(el).data('name')
                    }));
                });
                $responsibleSelect.append($('<option/>', {value: -1}));

                return self.getResponsibleSelectConfiguration.def.resolve($responsibleSelect.html(), select2Options, selectChangeHandler);
            }

            return self.getResponsibleSelectConfiguration.def;
        },

        setAsResponsibleSelect: function($select, selected) {
            return this.getResponsibleSelectConfiguration().then(function(selectHTML, select2Options, selectChangeHandler) {
                $select.select2('destroy');
                $select.html(selectHTML).css('width', '100%').addClass('form-control');
                if(selected !== undefined)
                    $select.val(selected);
                $select.select2(select2Options);
                $select.off('change').on('change', selectChangeHandler);
            });
        },

        getResponsibleName: function(responsibleID) {
            return $('.o_sign_parties_input_info').filter(function(i, el) {
                return (parseInt($(el).data('id')) === responsibleID);
            }).first().data('name');
        },

        getTypeData: function(id) {
            var self = this;

            if($.isEmptyObject(self.types)) {
                $("input[type='hidden'].o_sign_field_type_input_info").each(function(i, el) {
                    var $elem = $(el);
                    self.types[$elem.data('item-type-id')] = {
                        'id': $elem.data('item-type-id'),
                        'name': $elem.data('item-type-name'),
                        'type': $elem.data('item-type-type'),
                        'tip': $elem.data('item-type-tip'),
                        'placeholder': $elem.data('item-type-placeholder'),
                        'default_width': $elem.data('item-type-width'),
                        'default_height': $elem.data('item-type-height'),
                        'auto_field': $elem.data('item-type-auto')
                    };
                });
            }
            return self.types[id];
        },
    });

    /* ------------------------- */
    /*  Signature Dialog Widget  */
    /* ------------------------- */
    WIDGETS.SignatureDialog = Widget.extend({
        template: 'website_sign.signature_dialog',

        events: {
            'shown.bs.modal': function(e) {
                var width = this.$signatureField.width();
                var height = width / this.signatureRatio;

                this.$signatureField.empty().jSignature_custom({
                    'decor-color': 'transparent',
                    'background-color': '#FFF',
                    'color': '#000',
                    'lineWidth': 2,
                    'width': width,
                    'height': height
                });
                this.emptySignature = this.$signatureField.jSignature_custom("getData");

                this.$modeButtons.filter('.btn-primary').click();
                this.$('.modal-footer .btn-primary').prop('disabled', false).focus();
            },

            'click a.o_sign_mode': function(e) {
                this.$modeButtons.removeClass('btn-primary');
                $(e.target).addClass('btn-primary');
                this.$signatureField.jSignature_custom('reset');

                this.mode = $(e.target).data('mode');

                this.$selectStyleButton.toggle(this.mode === 'auto');
                this.$clearButton.toggle(this.mode === 'draw');
                this.$loadButton.toggle(this.mode === 'load');

                if(this.mode === 'load')
                    this.$loadButton.click();
                this.$signatureField.jSignature_custom((this.mode === 'draw')? "enable" : "disable");

                this.$fontDialog.hide().css('width', 0);
                this.$signerNameInput.trigger('input');
            },

            'input .o_sign_signer_name': function(e) {
                if(this.mode !== 'auto')
                    return true;
                this.printText(this.getSignatureFont(this.currentFont), this.getSignatureText());
            },

            'click .o_sign_select_style': function(e) {
                var self = this;

                self.$fontDialog.find('a').html('<div class="o_sign_loading"/>');
                self.$fontDialog.show().animate({'width': self.$fontDialog.find('a').first().height() * self.signatureRatio * 1.25}, 500, function() {
                    self.buildPreviewButtons();
                });
            },

            'mouseover .o_sign_font_dialog a': function(e) {
                this.currentFont = $(e.currentTarget).data('font-nb');
                this.$signerNameInput.trigger('input');
            },

            'click .o_sign_font_dialog a, .o_sign_signature': function(e) {
                this.$fontDialog.hide().css('width', 0);
            },

            'click .o_sign_clean': function (e) {
                this.$signatureField.jSignature_custom('reset');
            },

            'change .o_sign_load': function(e) {
                var self = this;

                var f = e.target.files[0];
                if(f.type.substr(0, 5) !== "image")
                    return false;

                var reader = new FileReader();
                reader.onload = function(e) {
                    self.printImage(this.result);
                };
                reader.readAsDataURL(f);
            },

            'click .modal-footer .btn-primary': function(e) {
                this.confirmFunction(this.$signerNameInput.val(), this.$signatureField.jSignature_custom("getData"));
            },
        },

        init: function(parent, signerName) {
            this._super(parent);

            this.signerName = signerName;

            this.signatureRatio = 3.0;
            this.signatureType = 'signature';

            this.emptySignature = null;
            this.fonts = null;

            this.currentFont = 0;
            this.mode = 'auto';

            this.confirmFunction = function() {};
        },

        start: function() {
            var self = this;

            self.$modeButtons = self.$('a.o_sign_mode');
            self.$signatureField = self.$(".o_sign_signature").first();
            self.$fontDialog = self.$(".o_sign_font_dialog").first();
            self.$fontSelection = self.$(".o_sign_font_selection").first();
            self.$clearButton = self.$('.o_sign_clean').first();
            self.$selectStyleButton = self.$('.o_sign_select_style').first();
            self.$loadButton = self.$('.o_sign_load').first();
            self.$signerNameInput = self.$(".o_sign_signer_name").first();

            return $.when(this._super(), self.getSignatureFont().then(function(data) {
                for(var i = 0 ; i < data.length ; i++)
                    self.$fontSelection.append($("<a data-font-nb='" + i + "'/>").addClass('btn btn-block'));
            }));
        },

        getSignatureText: function() {
            var text = this.$signerNameInput.val().replace(/[^\w-'" ]/g, '');
            if(this.signatureType === 'initial')
                return (text.split(' ').map(function(w) { return w[0]; }).join('.') + '.');
            return text;
        },

        getSVGText: function(font, text) {
            return ("data:image/svg+xml;base64," + btoa(qweb.render('website_sign.svg_text', {
                width: this.$signatureField.find('canvas')[0].width,
                height: this.$signatureField.find('canvas')[0].height,
                font: font,
                text: text,
                type: this.signatureType
            })));
        },

        printText: function(font, text) {
            return this.printImage(this.getSVGText(font, text));
        },

        printImage: function(imgSrc) {
            var self = this;

            if(self.printImage.def === undefined)
                self.printImage.def = (new $.Deferred()).resolve();

            self.printImage.def = self.printImage.def.then(function() {
                var newDef = new $.Deferred();

                var image = new Image;
                image.onload = function() {
                    var width = 0, height = 0;
                    var ratio = image.width/image.height

                    self.$signatureField.jSignature_custom('reset');
                    var $canvas = self.$signatureField.find('canvas'), context = $canvas[0].getContext("2d");

                    if(image.width / $canvas[0].width > image.height / $canvas[0].height) {
                        width = $canvas[0].width;
                        height = width / ratio;
                    }
                    else {
                        height = $canvas[0].height;
                        width = height * ratio;
                    }

                    setTimeout(function() {
                        $(context.drawImage(image, 0, 0, image.width, image.height, ($canvas[0].width - width)/2, ($canvas[0].height - height)/2, width, height)).promise().then(function() {
                            newDef.resolve();
                        });
                    }, 0);
                };
                image.src = imgSrc;

                return newDef;
            });

            return self.printImage.def;
        },

        buildPreviewButtons: function() {
            var self = this;

            self.$fontDialog.find('a').each(function(i, el) {
                var $img = $('<img/>', {src: self.getSVGText(self.getSignatureFont($(el).data('font-nb')), self.getSignatureText())});
                $(el).empty().append($img);
            });
        },

        getSignatureFont: function(no) {
            var self = this;

            if(!self.fonts)
                return ajax.jsonRpc('/sign/get_fonts', 'call', {}).then(function(data) {
                    return (self.fonts = data);
                });
            return ((no >= 0 && no < self.fonts.length)? self.fonts[no] : false);
        },

        onConfirm: function(fct) {
            this.confirmFunction = fct;
        },
    });

    /* --------------------------- */
    /*  Item Customization Dialog  */
    /* --------------------------- */
    WIDGETS.ItemCustomizationDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                var resp = parseInt(this.$responsibleSelect.find('select').val());
                var required = this.$('input[type="checkbox"]').prop('checked');

                websiteSign.currentRole = resp;
                this.$currentTarget.data({responsible: resp, required: required});

                this.$currentTarget.trigger('itemChange');
            },

            'click .o_sign_delete_field_button': function(e) {
                this.$currentTarget.trigger('itemDelete');
            }
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$responsibleSelect = this.$('.o_sign_responsible_select');
            return this._super();
        },

        setTarget: function($signatureItem) {
            this.$currentTarget = $signatureItem;
            websiteSign.setAsResponsibleSelect(this.$responsibleSelect.find('select'), $signatureItem.data('responsible'));
            this.$('input[type="checkbox"]').prop('checked', $signatureItem.data('required'));

            this.$('.modal-header .modal-title span').html('<span class="fa fa-long-arrow-right"/> ' + $signatureItem.prop('title') + ' Field');
        }
    });

    /* ------------------------------ */
    /*  Ask Multiple Initials Dialog  */
    /* ------------------------------ */
    WIDGETS.AskMultipleInitialsDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                this.updateTargetResponsible();
                this.$currentTarget.trigger('itemChange');
            },

            'click .modal-footer .btn-default': function(e) {
                this.updateTargetResponsible();
                this.$currentTarget.trigger('itemClone');
            }
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$responsibleSelect = this.$('.o_sign_responsible_select_initials');
            return this._super();
        },

        setTarget: function($signatureItem) {
            this.$currentTarget = $signatureItem;
            websiteSign.setAsResponsibleSelect(this.$responsibleSelect.find('select'), websiteSign.currentRole);
        },

        updateTargetResponsible: function() {
            var resp = parseInt(this.$responsibleSelect.find('select').val());
            websiteSign.currentRole = resp;
            this.$currentTarget.data('responsible', resp);
        },
    });

    /* --------------------------------- */
    /*  Signature Item Navigator Widget  */
    /* --------------------------------- */
    WIDGETS.SignatureItemNavigator = Widget.extend({
        className: 'o_sign_signature_item_navigator',

        events: {
            'click': 'onClick'
        },

        init: function(parent) {
            this._super(parent);

            this.iframeWidget = parent;
            this.started = false;
            this.isScrolling = false;
        },

        start: function() {
            this.$signatureItemNavLine = $('<div/>').addClass("o_sign_signature_item_navline");
            this.$signatureItemNavLine.insertBefore(this.$el);

            this.setTip('click to start');
            this.$el.focus();

            return this._super();
        },

        setTip: function(tip) {
            this.$el.html(tip);
        },

        onClick: function(e) {
            var self = this;

            if(!self.started) {
                self.started = true;

                self.iframeWidget.$iframe.prev().animate({'height': '0px', 'opacity': 0}, {
                    duration: 750,
                    progress: function() {
                        self.iframeWidget.resize(false);
                    },
                    complete: function() {
                        self.iframeWidget.$iframe.prev().hide();
                        self.iframeWidget.resize(true);

                        self.onClick();
                    }
                });
                
                return false;
            }

            var $toComplete = self.iframeWidget.checkSignatureItemsCompletion().sort(function(a, b) {
                return ($(a).data('order') || 0) - ($(b).data('order') || 0);
            });
            if($toComplete.length > 0)
                self.scrollToSignItem($toComplete.first());
        },

        scrollToSignItem: function($item) {
            var self = this;

            if(!self.started)
                return;

            var containerHeight = self.iframeWidget.$('#viewerContainer').outerHeight();
            var viewerHeight = self.iframeWidget.$('#viewer').outerHeight();

            var scrollOffset = containerHeight/4;
            var scrollTop = $item.offset().top - self.iframeWidget.$('#viewer').offset().top - scrollOffset;
            if(scrollTop + containerHeight > viewerHeight)
                scrollOffset += scrollTop + containerHeight - viewerHeight;
            if(scrollTop < 0)
                scrollOffset += scrollTop;
            scrollOffset += self.iframeWidget.$('#viewerContainer').offset().top - self.$el.outerHeight()/2 + parseInt($item.css('height'))/2;

            var duration = Math.min(1000, 
                5*(Math.abs(self.iframeWidget.$('#viewerContainer')[0].scrollTop - scrollTop) + Math.abs(parseFloat(self.$el.css('top')) - scrollOffset)));

            this.isScrolling = true;
            self.iframeWidget.$('#viewerContainer').animate({'scrollTop': scrollTop}, duration);
            self.$el.add(self.$signatureItemNavLine).animate({'top': scrollOffset}, duration, 'swing', function() {
                if($item.val() === "" && !$item.data('signature'))
                    self.setTip(websiteSign.getTypeData($item.data('type'))['tip']);
                
                self.iframeWidget.refreshSignatureItems();
                $item.focus();
                this.isScrolling = false;
            });

            self.iframeWidget.$('.ui-selected').removeClass('ui-selected');
            $item.addClass('ui-selected').focus();
        },
    });

    /* ------------------- */
    /*  PDF Iframe Widget  */
    /* ------------------- */
    WIDGETS.PDFIframe = Widget.extend({
        events: {
            'keydown .page .ui-selected': function(e) {
                if((e.keyCode || e.which) !== 9)
                    return true;

                e.preventDefault(); 
                this.signatureItemNav.onClick();
            },

            'click #toolbarContainer': 'delayedRefresh',

            'itemChange .o_sign_signature_item': function(e) {
                this.updateSignatureItem($(e.target));
                this.$iframe.trigger('templateChange');
            },

            'itemDelete .o_sign_signature_item': function(e) {
                this.deleteSignatureItem($(e.target));
                this.$iframe.trigger('templateChange');
            },

            'itemClone .o_sign_signature_item': function(e) {
                var $target = $(e.target);
                this.updateSignatureItem($target);
                for(var i = 1 ; i <= this.nbPages ; i++) {
                    var ignore = false;
                    for(var j = 0 ; j < this.configuration[i].length ; j++) {
                        if(websiteSign.getTypeData(this.configuration[i][j].data('type'))['type'] === 'signature')
                            ignore = true;
                    }
                    if(ignore)
                        continue;

                    var $newElem = $target.clone(true);
                    this.enableCustom($newElem);
                    this.configuration[i].push($newElem);
                }
                this.deleteSignatureItem($target);
                this.refreshSignatureItems();
                this.$iframe.trigger('templateChange');
            }
        },

        init: function(parent, $iframe, editMode) {
            this._super(parent);

            this.$iframe = $iframe;

            this.nbPages = 0;

            this.editMode = editMode;
            this.readonlyFields = (this.$iframe.attr('readonly') === "readonly") || editMode;
            this.pdfView = window.location.href.indexOf('pdfview') > -1 || (this.$iframe.attr('readonly') === "readonly");

            this.role = parseInt($('#o_sign_input_current_role').val()) || 0;

            this.$fieldTypeToolbar = null;
            this.currentFieldType = false;
            this.configuration = {};

            this.types = {};

            this.refreshTimer = null;

            this.fullyLoaded = new $.Deferred();
        },

        start: function(attachmentLocation, $signatureItemsInfo) {
            var self = this;

            var resizeWindowTimer = null;
            $(window).on('resize', function(e) {
                clearTimeout(resizeWindowTimer);
                resizeWindowTimer = setTimeout(function() {self.resize(true);}, 250);
            });

            var viewerURL = ((!self.editMode)? "../" : "") + "../../website_sign/static/lib/pdfjs/web/viewer.html?file=";
            viewerURL += encodeURIComponent(attachmentLocation).replace(/'/g,"%27").replace(/"/g,"%22") + "#page=1&zoom=page-width";
            self.$iframe.attr('src', viewerURL);
            
            $('body').css('overflow', 'hidden');

            self.waitForPDF($signatureItemsInfo);
            return $.when(self._super(), self.fullyLoaded.promise());
        },

        waitForPDF: function($signatureItemsInfo) {
            var self = this;

            if(self.$iframe.contents().find('#errorMessage').is(":visible"))
                return alert('Need a valid PDF to add signature fields !');

            var nbPages = self.$iframe.contents().find('.page').length;
            var nbLayers = self.$iframe.contents().find('.textLayer').length;
            if(nbPages > 0 && nbLayers > 0) {
                self.nbPages = nbPages;
                self.doPDFPostLoad($signatureItemsInfo);
            }
            else
                setTimeout(function() { self.waitForPDF($signatureItemsInfo); }, 50);
        },

        resize: function(refresh) {
            this.$iframe.css('height', $('body').outerHeight()-this.$iframe.offset().top);
            if(refresh)
                this.refreshSignatureItems();
        },

        doPDFPostLoad: function($signatureItemsInfo) {
            var self = this;

            self.setElement(self.$iframe.contents().find('html'));
            self.resize(false);

            self.$('#openFile, #pageRotateCw, #pageRotateCcw, #pageRotateCcw').add(self.$('#lastPage').next()).hide();
            self.$('button#print').prop('title', "Print original document");
            self.$('button#download').prop('title', "Download original document");
            self.$('button#zoomOut').click();
            
            for(var i = 1 ; i <= self.nbPages ; i++)
                self.configuration[i] = [];

            var $cssLink = $("<link/>", {
                rel: "stylesheet",
                type: "text/css",
                href: "/website_sign/static/src/css/iframe.css"
            });
            var $faLink = $("<link/>", {
                rel: "stylesheet",
                type: "text/css",
                href: "/web/static/lib/fontawesome/css/font-awesome.css"
            });
            var $jqueryLink = $("<link/>", {
                rel: "stylesheet",
                type: "text/css",
                href: "/web/static/lib/jquery.ui/jquery-ui.css"
            });
            var $jqueryScript = $("<script></script>", {
                type: "text/javascript",
                src: "/web/static/lib/jquery.ui/jquery-ui.js"
            });
            self.$('head').append($cssLink, $faLink, $jqueryLink, $jqueryScript);

            var waitFor = [];

            if(self.editMode) {
                if(self.$iframe.attr('disabled') === 'disabled') {
                    self.$('#viewer').fadeTo('slow', 0.75);
                    var $div = $('<div/>').css({
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: "100%",
                        'z-index': 110,
                        opacity: 0.75
                    });
                    self.$('#viewer').css('position', 'relative').prepend($div);
                    $div.on('click mousedown mouseup mouveover mouseout', function(e) {
                        return false;
                    });
                }
                else {
                    self.$hBarTop = $('<div/>');
                    self.$hBarBottom = $('<div/>');
                    self.$hBarTop.add(self.$hBarBottom).css({
                        position: 'absolute',
                        "border-top": "1px dashed orange",
                        width: "100%",
                        height: 0,
                        "z-index": 103,
                        left: 0
                    });
                    self.$vBarLeft = $('<div/>');
                    self.$vBarRight = $('<div/>');
                    self.$vBarLeft.add(self.$vBarRight).css({
                        position: 'absolute',
                        "border-left": "1px dashed orange",
                        width: 0,
                        height: "10000px",
                        "z-index": 103,
                        top: 0
                    });

                    var $fieldTypeButtons = $('.o_sign_field_type_button');
                    self.$fieldTypeToolbar = $('<div/>').addClass('o_sign_field_type_toolbar');
                    self.$fieldTypeToolbar.prependTo(self.$('#viewerContainer'));
                    $fieldTypeButtons.detach().appendTo(self.$fieldTypeToolbar).draggable({
                        cancel: false,
                        helper: function(e) {
                            self.currentFieldType = $(this).data('item-type-id');
                            
                            var type = websiteSign.getTypeData(self.currentFieldType);
                            var $signatureItem = self.createSignatureItem(self.currentFieldType, true, websiteSign.currentRole, 0, 0, type["default_width"], type["default_height"]);

                            if(!e.ctrlKey)
                                self.$('.o_sign_signature_item').removeClass('ui-selected');
                            $signatureItem.addClass('o_sign_signature_item_to_add ui-selected');

                            self.$('.page').first().append($signatureItem);
                            self.updateSignatureItem($signatureItem);
                            $signatureItem.css('width', $signatureItem.css('width')).css('height', $signatureItem.css('height')); // Convert % to px
                            $signatureItem.detach();
                            
                            return $signatureItem;
                        }
                    });
                    $fieldTypeButtons.each(function(i, el) {
                        self.enableCustomBar($(el));
                    });

                    self.$('.page').droppable({
                        accept: '*',
                        tolerance: 'touch',
                        drop: function(e, ui) {
                            if(!ui.helper.hasClass('o_sign_signature_item_to_add'))
                                return true;

                            var $parent = $(e.target);
                            var pageNo = parseInt($parent.prop('id').substr('pageContainer'.length));

                            ui.helper.removeClass('o_sign_signature_item_to_add');
                            var $signatureItem = ui.helper.clone(true).removeClass().addClass('o_sign_signature_item o_sign_signature_item_required');

                            var posX = (ui.offset.left - $parent.find('.textLayer').offset().left) / $parent.innerWidth();
                            var posY = (ui.offset.top - $parent.find('.textLayer').offset().top) / $parent.innerHeight();
                            $signatureItem.data({posx: posX, posy: posY});

                            self.configuration[pageNo].push($signatureItem);
                            self.refreshSignatureItems();
                            self.updateSignatureItem($signatureItem);
                            self.enableCustom($signatureItem);

                            self.$iframe.trigger('templateChange');

                            if(websiteSign.getTypeData($signatureItem.data('type'))['type'] === 'initial') {
                                self.askMultipleInitialsDialog.setTarget($signatureItem);
                                self.askMultipleInitialsDialog.$el.modal('show');
                            }

                            self.currentFieldType = false;

                            return false;
                        }
                    });

                    self.$('#viewer').selectable({
                        appendTo: self.$('body'), 
                        filter: '.o_sign_signature_item'
                    });

                    var keyFct = function(e) {
                        if(e.which !== 46)
                            return true;

                        self.$('.ui-selected').each(function(i, el) {
                            self.deleteSignatureItem($(el));
                        });
                        self.$iframe.trigger('templateChange');
                    };
                    $(document).on('keyup', keyFct);
                    self.$el.on('keyup', keyFct);
                }

                self.itemCustomDialog = new WIDGETS.ItemCustomizationDialog(self, $('.o_sign_signature_item_custom_dialog').first());
                waitFor.push(self.itemCustomDialog.start());

                self.askMultipleInitialsDialog = new WIDGETS.AskMultipleInitialsDialog(self, $('.o_sign_initial_all_page_dialog').first());
                waitFor.push(self.askMultipleInitialsDialog.start());
            }
            else {
                self.signatureItemNav = new WIDGETS.SignatureItemNavigator(self);
                waitFor.push(self.signatureItemNav.prependTo(self.$('#viewerContainer')));
            }

            $signatureItemsInfo.sort(function(a, b) {
                var $a = $(a), $b = $(b);

                if($a.data('page') !== $b.data('page'))
                    return ($a.data('page') - $b.data('page'));

                if(Math.abs($a.data('posy') - $b.data('posy')) > 0.01)
                    return ($a.data('posy') - $b.data('posy'));
                else
                    return ($a.data('posx') - $b.data('posx'));
            }).each(function(i, el){
                var $elem = $(el);
                var $signatureItem = self.createSignatureItem(
                    $elem.data('type'), $elem.data('required') === "True", parseInt($elem.data('responsible')) || 0,
                    parseFloat($elem.data('posx')), parseFloat($elem.data('posy')), $elem.data('width'), $elem.data('height'),
                    $elem.data('item-value'));
                $signatureItem.data('item-id', $elem.data('item-id'));
                $signatureItem.data('order', i);

                self.configuration[parseInt($elem.data('page'))].push($signatureItem);
            }); 

            $.when.apply($, waitFor).then(function() {
                self.refreshSignatureItems();

                self.$('.o_sign_signature_item').each(function(i, el) {
                    if(self.editMode)
                        self.enableCustom($(el));
                    self.updateSignatureItem($(el));
                });

                self.updateFontSize();

                if(!self.editMode)
                    self.checkSignatureItemsCompletion();

                self.$('#viewerContainer').on('scroll', function(e) {
                    if(!self.editMode && self.signatureItemNav.started)
                        self.signatureItemNav.setTip('next');
                    if(self.editMode || !self.signatureItemNav.isScrolling)
                        self.delayedRefresh();
                });

                self.$('#viewerContainer').css('visibility', 'visible').animate({'opacity': 1}, 1000);

                self.fullyLoaded.resolve();
            });
        },

        delayedRefresh: function() {
            var self = this;

            clearTimeout(self.refreshTimer);
            self.refreshTimer = setTimeout(function() {
                self.refreshSignatureItems();
            }, 250);
        },

        refreshSignatureItems: function() {
            clearTimeout(this.refreshTimer);
            for(var page in this.configuration) {
                var $pageContainer = this.$('body #pageContainer' + page);
                for(var i = 0 ; i < this.configuration[page].length ; i++)
                    $pageContainer.append(this.configuration[page][i].detach());
            }
            this.updateFontSize();
        },

        updateFontSize: function() {
            var self = this;

            var normalSize = self.$('.page').first().innerHeight() * 0.015;

            self.$('.o_sign_signature_item').each(function(i, el) {
                var $elem = $(el);
                var size = parseFloat($elem.css('height'));
                if($.inArray(websiteSign.getTypeData($elem.data('type'))['type'], ['signature', 'initial', 'textarea']) > -1)
                    size = normalSize;

                $elem.css('font-size', size * 0.8);
            });
        },

        createSignatureItem: function(typeID, required, responsible, posX, posY, width, height, value) {
            var self = this;

            var readonly = self.readonlyFields || (responsible > 0 && responsible !== self.role);
            var type = websiteSign.getTypeData(typeID);

            var $signatureItem = $(qweb.render('website_sign.signature_item', {
                readonly: readonly,
                type: type['type'],
                value: (value)? ("" + value).split('\n').join('<br/>') : "",
                placeholder: type['placeholder']
            }));

            if(!readonly) {
                if(type['type'] === "signature" || type['type'] === "initial") {
                    $signatureItem.on('click', function(e) {
                        var $signedItems = self.$('.o_sign_signature_item').filter(function(i) {
                            var $item = $(this);
                            return ($item.data('type') === type['id']
                                        && $item.data('signature') && $item.data('signature') !== $signatureItem.data('signature')
                                        && ($item.data('responsible') <= 0 || $item.data('responsible') === $signatureItem.data('responsible')));
                        });
                        
                        if($signedItems.length > 0) {
                            $signatureItem.data('signature', $signedItems.first().data('signature'));
                            $signatureItem.html('<span class="o_sign_helper"/><img src="' + $signatureItem.data('signature') + '"/>');
                            $signatureItem.trigger('input');
                        }
                        else {
                            websiteSign.signatureDialog.signatureType = type['type'];
                            websiteSign.signatureDialog.signatureRatio = parseFloat($signatureItem.css('width'))/parseFloat($signatureItem.css('height'));
                            websiteSign.signatureDialog.$el.modal('show');

                            websiteSign.signatureDialog.onConfirm(function(name, signature) {
                                if(signature !== websiteSign.signatureDialog.emptySignature) {
                                    $signatureItem.data('signature', signature);
                                    $signatureItem.html('<span class="o_sign_helper"/><img src="' + $signatureItem.data('signature') + '"/>');
                                }
                                else {
                                    $signatureItem.removeData('signature');
                                    $signatureItem.html("<span class='o_sign_helper'/>" + type['placeholder']);
                                }

                                $signatureItem.trigger('input').focus();
                                websiteSign.signatureDialog.$el.modal('hide');
                            });
                        }
                    });
                }

                if(type['auto_field']) {
                    $signatureItem.on('focus', function(e) {
                        if($signatureItem.val() === "") {
                            $signatureItem.val(type['auto_field']);
                            $signatureItem.trigger('input');
                        }
                    });
                }

                $signatureItem.on('input', function(e) {
                    self.checkSignatureItemsCompletion(self.role);
                    self.signatureItemNav.setTip('next');
                });
            }

            $signatureItem.data({type: type['id'], required: required, responsible: responsible, posx: posX, posy: posY, width: width, height: height});
            return $signatureItem;
        },

        deleteSignatureItem: function($item) {
            var pageNo = parseInt($item.parent().prop('id').substr('pageContainer'.length));
            $item.remove();
            for(var i in this.configuration[pageNo]) {
                if(this.configuration[pageNo][i].data('posx') === $item.data('posx') && this.configuration[pageNo][i].data('posy') === $item.data('posy'))
                    this.configuration[pageNo].splice(i, 1);
            }
        },

        enableCustom: function($signatureItem) {
            var self = this;

            $signatureItem.prop('title', websiteSign.getTypeData($signatureItem.data('type'))['name']);

            var $configArea = $signatureItem.find('.o_sign_config_area');
            $configArea.show();

            $configArea.find('.fa.fa-arrows').on('mouseup', function(e) {
                if(!e.ctrlKey) {
                    self.$('.o_sign_signature_item').filter(function(i) {
                        return (this !== $signatureItem[0]);
                    }).removeClass('ui-selected');
                }
                $signatureItem.toggleClass('ui-selected');
            });

            $signatureItem.add($configArea.find('.o_sign_responsible_display')).on('mousedown', function(e) {
                if(e.target !== e.currentTarget)
                    return true;

                self.$('.ui-selected').removeClass('ui-selected');
                $signatureItem.addClass('ui-selected');

                self.itemCustomDialog.setTarget($signatureItem);
                self.itemCustomDialog.$el.modal("show");
            });

            $signatureItem.draggable({containment: "parent", handle: ".fa-arrows"}).resizable({containment: "parent"}).css('position', 'absolute');

            $signatureItem.on('dragstart resizestart', function(e, ui) {
                if(!e.ctrlKey)
                    self.$('.o_sign_signature_item').removeClass('ui-selected');
                $signatureItem.addClass('ui-selected');
            });

            $signatureItem.on('dragstop', function(e, ui) {
                $signatureItem.data('posx', Math.round((ui.position.left / $signatureItem.parent().innerWidth())*1000)/1000);
                $signatureItem.data('posy', Math.round((ui.position.top / $signatureItem.parent().innerHeight())*1000)/1000);
            });

            $signatureItem.on('resizestop', function(e, ui) {
                $signatureItem.data('width', Math.round(ui.size.width/$signatureItem.parent().innerWidth()*1000)/1000);
                $signatureItem.data('height', Math.round(ui.size.height/$signatureItem.parent().innerHeight()*1000)/1000);
            });

            $signatureItem.on('dragstop resizestop', function(e, ui) {
                self.updateSignatureItem($signatureItem);
                self.$iframe.trigger('templateChange');
                $signatureItem.removeClass('ui-selected');
            });

            self.enableCustomBar($signatureItem);
        },

        enableCustomBar: function($item) {
            var self = this;

            var start = function($helper) {
                self.$hBarTop.detach().insertAfter($helper).show();
                self.$hBarBottom.detach().insertAfter($helper).show();
                self.$vBarLeft.detach().insertAfter($helper).show();
                self.$vBarRight.detach().insertAfter($helper).show();
            };
            var process = function($helper, position) {
                self.$hBarTop.css('top', position.top);
                self.$hBarBottom.css('top', position.top+parseFloat($helper.css('height'))-1);
                self.$vBarLeft.css('left', position.left);
                self.$vBarRight.css('left', position.left+parseFloat($helper.css('width'))-1);
            };
            var end = function() {
                self.$hBarTop.hide();
                self.$hBarBottom.hide();
                self.$vBarLeft.hide();
                self.$vBarRight.hide();
            };

            $item.on('dragstart resizestart', function(e, ui) {
                start(ui.helper);
            });

            $item.find('.o_sign_config_area .fa.fa-arrows').on('mousedown', function(e) {
                start($item);
                process($item, $item.position());
            });

            $item.on('drag resize', function(e, ui) {
                process(ui.helper, ui.position);
            });

            $item.on('dragstop resizestop', function(e, ui) {
                end();
            });

            $item.find('.o_sign_config_area .fa.fa-arrows').on('mouseup', function(e) {
                end();
            });
        },

        updateSignatureItem: function($signatureItem) {
            var posX = $signatureItem.data('posx'), posY = $signatureItem.data('posy');
            var width = $signatureItem.data('width'), height = $signatureItem.data('height');

            if(posX < 0)
                posX = 0;
            else if(posX+width > 1.0)
                posX = 1.0-width;
            if(posY < 0)
                posY = 0;
            else if(posY+height > 1.0)
                posY = 1.0-height;

            $signatureItem.data({posx: Math.round(posX*1000)/1000, posy: Math.round(posY*1000)/1000});
            $signatureItem.css({'left': posX*100 + '%', 'top': posY*100 + '%', 'width': width*100 + '%', 'height': height*100 + '%'});

            if(this.editMode) {
                var responsibleName = websiteSign.getResponsibleName($signatureItem.data('responsible'));
                $signatureItem.find('.o_sign_responsible_display').html(responsibleName).prop('title', responsibleName);
            }

            var resp = $signatureItem.data('responsible');
            $signatureItem.toggleClass('o_sign_signature_item_required', ($signatureItem.data('required') && (this.editMode || resp <= 0 || resp === this.role)));
            $signatureItem.toggleClass('o_sign_signature_item_pdfview', (this.pdfView || (resp !== this.role && resp > 0 && !this.editMode)));
        },

        checkSignatureItemsCompletion: function() {
            var $toComplete = this.$('.o_sign_signature_item.o_sign_signature_item_required:not(.o_sign_signature_item_pdfview)').filter(function(i, el) {
                var $elem = $(el);
                return !(($elem.val() && $elem.val().trim()) || $elem.data('signature'));
            });

            this.signatureItemNav.$el.add(this.signatureItemNav.$signatureItemNavLine).toggle($toComplete.length > 0);
            this.$iframe.trigger(($toComplete.length > 0)? 'pdfToComplete' : 'pdfCompleted');

            return $toComplete;
        },

        disableItems: function() {
            this.$('.o_sign_signature_item').addClass('o_sign_signature_item_pdfview').removeClass('ui-selected');
        }
    });

    /* --------------------------------- */
    /*  Create Signature Request Dialog  */
    /* --------------------------------- */
    WIDGETS.CreateSignatureRequestDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                this.sendDocument();
            },
        },

        init: function(parent, $root, templateID) {
            this._super(parent);
            this.setElement($root);

            this.templateID = templateID;
        },

        start: function() {
            this.$subjectInput = this.$('.o_sign_subject_input').first();
            this.$messageInput = this.$('.o_sign_message_textarea').first();
            this.$referenceInput = this.$('.o_sign_reference_input').first();

            return this._super();
        },

        launch: function(rolesToChoose, templateName) {
            this.$subjectInput.val('Signature Request - ' + templateName);
            var defaultRef = templateName + this.$referenceInput.data('endref');
            this.$referenceInput.val(defaultRef).attr('placeholder', defaultRef);

            this.$('.o_sign_warning_message_no_field').first().toggle($.isEmptyObject(rolesToChoose));
            this.$('.o_sign_request_signers .o_sign_new_signer').remove();

            websiteSign.setAsPartnerSelect(this.$('.o_sign_request_signers .form-group select')); // Followers
            
            if($.isEmptyObject(rolesToChoose))
                this.addSigner(0, "Signers", true);
            else {
                var roleIDs = Object.keys(rolesToChoose).sort();
                for(var i = 0 ; i < roleIDs.length ; i++) {
                    var roleID = roleIDs[i];
                    if(roleID !== 0)
                        this.addSigner(roleID, rolesToChoose[roleID], false);
                }
            }

            this.$el.modal('show');
        },

        addSigner: function(roleID, roleName, multiple) {
            var $newSigner = $('<div/>').addClass('o_sign_new_signer form-group');

            $newSigner.append($('<label/>').addClass('col-md-3 control-label').html(roleName).data('role', roleID));
            
            var $signerInfo = $('<select placeholder="Write email or search contact..."/>');
            if(multiple)
                $signerInfo.attr('multiple', 'multiple');

            var $signerInfoDiv = $('<div/>').addClass('col-md-9');
            $signerInfoDiv.append($signerInfo);

            $newSigner.append($signerInfoDiv);

            websiteSign.setAsPartnerSelect($signerInfo);

            this.$('.o_sign_request_signers').first().prepend($newSigner);
        },

        sendDocument: function() {
            var self = this;

            var completedOk = true;
            self.$('.o_sign_new_signer').each(function(i, el) {
                var $elem = $(el);
                var partnerIDs = $elem.find('select').val();
                if(!partnerIDs || partnerIDs.length <= 0) {
                    completedOk = false;
                    $elem.addClass('has-error');
                    $elem.one('focusin', function(e) {
                        $elem.removeClass('has-error');
                    });
                }
            });
            if(!completedOk)
                return false;

            var waitFor = [];

            var signers = [];
            self.$('.o_sign_new_signer').each(function(i, el) {
                var $elem = $(el);
                var selectDef = websiteSign.processPartnersSelectionThen($elem.find('select'), function(partners) {
                    for(var p = 0 ; p < partners.length ; p++) {
                        signers.push({
                            'partner_id': partners[p],
                            'role': parseInt($elem.find('label').data('role'))
                        });
                    }
                });
                if(selectDef !== false)
                    waitFor.push(selectDef);
            });

            var followers = [];
            var followerDef = websiteSign.processPartnersSelectionThen(self.$('#o_sign_followers_select'), function(partners) {
                followers = partners;
            });
            if(followerDef !== false)
                waitFor.push(followerDef);

            var subject = self.$subjectInput.val() || self.$subjectInput.attr('placeholder');
            var reference = self.$referenceInput.val() || self.$referenceInput.attr('placeholder');
            var message = self.$messageInput.val();
            $.when.apply($, waitFor).then(function(result) {
                ajax.jsonRpc("/sign/create_document/" + self.templateID, 'call', {
                    'signers': signers,
                    'reference': reference,
                    'followers': followers,
                    'subject': subject,
                    'message': message,
                    'send': true
                }).then(function(requestID) {
                    window.location.href = "/sign/document/" + requestID + "?pdfview&message=2";
                });
            });
        },
    });

    /* ----------------------- */
    /*  Share Template Dialog  */
    /* ----------------------- */
    WIDGETS.ShareTemplateDialog = Widget.extend({
        events: {
            'focus input': function(e) {
                $(e.target).select();
            },
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$linkInput = this.$('input').first();
            return this._super();
        },

        launch: function(templateID) {
            var self = this;

            var $formGroup = self.$linkInput.closest('.form-group');
            $formGroup.hide();
            $formGroup.next().hide();
            var linkStart = window.location.href.substr(0, window.location.href.indexOf('/sign')) + '/sign/';

            ajax.jsonRpc("/sign/share/" + templateID, 'call', {}).then(function(link) {
                self.$linkInput.val((link)? (linkStart + link) : '');
                $formGroup.toggle(link);
                $formGroup.next().toggle(!link);

                self.$el.modal('show');
            });
        },
    });

    /* ---------------------- */
    /*  Add Followers Dialog  */
    /* ---------------------- */
    WIDGETS.AddFollowersDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                websiteSign.processPartnersSelectionThen(this.$select, function(partners) {
                    ajax.jsonRpc($(e.target).data('ref'), 'call', {
                        'followers': partners
                    }).then(function(requestID) {
                        window.location.href = "/sign/document/" + requestID + "?pdfview";
                    });
                });
            },
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            this.$select = this.$('#o_sign_followers_select');
            return this._super();
        },

        launch: function() {
            websiteSign.setAsPartnerSelect(this.$select);
            this.$el.modal('show');
        },
    });

    /* ---------------------- */
    /*  Public Signer Dialog  */
    /* ---------------------- */
    WIDGETS.PublicSignerDialog = Widget.extend({
        events: {
            'click .modal-footer .btn-primary': function(e) {
                var self = this;

                var name = self.$el.find('input').eq(0).val();
                var mail = self.$el.find('input').eq(1).val();
                if(!name || !mail || mail.indexOf('@') < 0) {
                    self.$el.find('input').eq(0).closest('.form-group').toggleClass('has-error', !name);
                    self.$el.find('input').eq(1).closest('.form-group').toggleClass('has-error', !mail || mail.indexOf('@') < 0);
                    return false;
                }

                ajax.jsonRpc($(e.target).data('ref'), 'call', {
                    'name': name,
                    'mail': mail
                }).then(function() {
                    self.$el.modal('hide');
                    return self.thenFunction();
                });
            }
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);

            this.thenFunction = function() {};
        },

        launch: function(name, mail, thenFunction) {
            if(this.$el.length <= 0)
                return thenFunction();

            this.$el.find('input').eq(0).val(name);
            this.$el.find('input').eq(1).val(mail);

            this.thenFunction = thenFunction;
            this.$el.modal('show');
        },
    });

    /* ------------------ */
    /*  Thank You Dialog  */
    /* ------------------ */
    WIDGETS.ThankYouDialog = Widget.extend({
        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },
    });

    /* ------------------------- */
    /*  WebsiteSign Page Widget  */
    /* ------------------------- */
    WIDGETS.WebsiteSignPage = Widget.extend({
        events: {
            'click .fa-pencil': function(e) {
                this.$templateNameInput.focus().select();
            },

            'input .o_sign_template_name_input': function(e) {
                this.$templateNameInput.attr('size', this.$templateNameInput.val().length);
            },

            'change .o_sign_template_name_input': function(e) {
                this.saveTemplate();
                if(this.$templateNameInput.val() === "")
                    this.$templateNameInput.val(this.initialTemplateName);
            },

            'click .o_sign_send_template_button': function(e) {
                this.saveTemplate();
                this.createSignatureRequestDialog.launch(this.rolesToChoose, this.$templateNameInput.val());
            },

            'click .o_sign_share_template_button': function(e) {
                this.shareTemplateDialog.launch(this.templateID);
            },

            'click .o_sign_cancel_request_button': function(e) {
                ajax.jsonRpc($(e.target).data('ref'), 'call', {}).then(function(data) {
                    window.location.href = "/sign";
                });
            },

            'click .o_sign_resend_access_button.fa': function(e) {
                $(e.target).removeClass('fa fa-envelope').html('...');
                ajax.jsonRpc("/sign/resend_access", 'call', {
                    'id': parseInt($(e.target).data('id'))
                }).then(function(data) {
                    $(e.target).html("Resent !");
                });
            },

            'click .o_sign_add_followers_button': function(e) {
                this.addFollowersDialog.launch();
            },

            'templateChange iframe.o_sign_pdf_iframe': function(e) {
                this.saveTemplate();
            },

            'click .o_sign_duplicate_signature_template': function(e) {
                this.saveTemplate(true);
            },

            'pdfToComplete iframe.o_sign_pdf_iframe': function(e) {
                this.$validateBanner.hide().css('opacity', 0);
            },

            'pdfCompleted iframe.o_sign_pdf_iframe': function(e) {
                this.$validateBanner.show().animate({'opacity': 1}, 500);
            },

            'click .o_sign_validate_banner button': 'signItemDocument',
            'click .o_sign_sign_document_button': 'signDocument',
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);

            this.iframeWidget = null;
            this.rolesToChoose = {};
        },

        start: function() {
            var self = this;

            var defStarts = [self._super()];

            self.attachmentLocation = self.$('#o_sign_input_attachment_location').val();
            self.templateID = parseInt(self.$('#o_sign_input_signature_request_template_id').val());
            self.requestID = parseInt(self.$('#o_sign_input_signature_request_id').val());

            self.$templateNameInput = self.$('.o_sign_template_name_input').first();
            self.$templateNameInput.trigger('input');
            self.initialTemplateName = self.$templateNameInput.val();

            self.$iframe = self.$('iframe.o_sign_pdf_iframe').first();
            
            self.$buttonSendTemplate = self.$('.o_sign_send_template_button');
            self.$validateBanner = self.$('.o_sign_validate_banner').first();

            var editMode = !self.requestID;
            if(editMode) {
                self.createSignatureRequestDialog = new WIDGETS.CreateSignatureRequestDialog(self, self.$('.o_sign_create_signature_request_dialog').first(), self.templateID);
                defStarts.push(self.createSignatureRequestDialog.start());
                self.shareTemplateDialog = new WIDGETS.ShareTemplateDialog(self, self.$('.o_sign_share_template_dialog').first());
                defStarts.push(self.shareTemplateDialog.start());
            }
            else {
                self.addFollowersDialog = new WIDGETS.AddFollowersDialog(self, self.$('.o_sign_add_followers_dialog').first());
                defStarts.push(self.addFollowersDialog.start());
                self.publicSignerDialog = new WIDGETS.PublicSignerDialog(self, self.$('.o_sign_public_signer_dialog').first());
                defStarts.push(self.publicSignerDialog.start());
                self.thankYouDialog = new WIDGETS.ThankYouDialog(self, self.$('.o_sign_thank_you_dialog'));
                defStarts.push(self.thankYouDialog.start());
            }

            if(self.$iframe.length > 0) {
                self.$buttonSendTemplate.prop('disabled', true);

                self.iframeWidget = new WIDGETS.PDFIframe(self, self.$iframe, editMode);
                defStarts.push(self.iframeWidget.start(self.attachmentLocation, self.$iframe.parent().find("input[type='hidden'].o_sign_item_input_info")).then(function(e) {
                    self.$buttonSendTemplate.prop('disabled', false);
                }));       
            }

            return $.when.apply($, defStarts);
        },

        saveTemplate: function(duplicate) {
            duplicate = (duplicate === undefined)? false : duplicate;

            this.rolesToChoose = {};
            var data = {};
            var newId = 0;
            var configuration = (this.iframeWidget)? this.iframeWidget.configuration : {};
            for(var page in configuration) {
                for(var i = 0 ; i < configuration[page].length ; i++) {
                    var resp = configuration[page][i].data('responsible');

                    data[configuration[page][i].data('item-id') || (newId--)] = {
                        'type_id': configuration[page][i].data('type'),
                        'required': configuration[page][i].data('required'),
                        'responsible_id': resp,
                        'page': page,
                        'posX': configuration[page][i].data('posx'),
                        'posY': configuration[page][i].data('posy'),
                        'width': configuration[page][i].data('width'),
                        'height': configuration[page][i].data('height'),
                    };

                    this.rolesToChoose[resp] = websiteSign.getResponsibleName(resp);
                }
            }

            var $majInfo = this.$('.o_sign_template_saved_info').first();

            ajax.jsonRpc("/sign/update_template/" + this.templateID + ((duplicate)? '/duplicate' : '/update'), 'call', {
                'signature_items': data,
                'name': this.$templateNameInput.val() || this.initialTemplateName
            }).then(function (templateID) {
                if(!duplicate)
                    $majInfo.stop().css('opacity', 1).animate({'opacity': 0}, 1500);
                else
                    window.location.href = '/sign/template/' + templateID;
            });
        },

        signItemDocument: function(e) {
            var self = this;

            var mail = "";
            self.iframeWidget.$('.o_sign_signature_item').each(function(i, el){
                if($(el).val() && $(el).val().indexOf('@') >= 0)
                    mail = $(el).val();
            });

            self.publicSignerDialog.launch(websiteSign.signatureDialog.$signerNameInput.val(), mail, function() {
                var ok = true;

                var signatureValues = {};
                outloop:
                for(var page in self.iframeWidget.configuration) {
                    for(var i = 0 ; i < self.iframeWidget.configuration[page].length ; i++) {
                        var $elem = self.iframeWidget.configuration[page][i];
                        var resp = parseInt($elem.data('responsible')) || 0;
                        if(resp > 0 && resp !== self.iframeWidget.role) {
                            continue;
                        }

                        var value = ($elem.val() && $elem.val().trim())? $elem.val() : false;
                        if($elem.data('signature'))
                            value = (($elem.data('signature') !== websiteSign.signatureDialog.emptySignature)? $elem.data('signature') : false);

                        if(!value) {
                            if($elem.data('required')) {
                                ok = false;
                                break outloop;
                            }
                            continue;
                        }

                        signatureValues[parseInt($elem.data('item-id'))] = value;
                    }
                }

                if(!ok)
                    return alert("Some fields must be completed !\nIf there is a problem, please try reloading the page.");

                self.iframeWidget.disableItems();
                self.thank(ajax.jsonRpc($(e.target).data('action'), 'call', {
                    sign: signatureValues
                }));
            });
        },

        signDocument: function(e) {
            var self = this;

            websiteSign.signatureDialog.onConfirm(function(name, signature) {
                var isEmpty = ((signature)? (websiteSign.signatureDialog.emptySignature === signature) : true);

                websiteSign.signatureDialog.$('.o_sign_signer_info').toggleClass('has-error', !name);
                websiteSign.signatureDialog.$('.o_sign_signature_draw').toggleClass('panel-danger', isEmpty).toggleClass('panel-default', !isEmpty);
                if(isEmpty || !name)
                    return false;

                websiteSign.signatureDialog.$('.modal-footer .btn-primary').prop('disabled', true);
                websiteSign.signatureDialog.$el.modal('hide');

                self.publicSignerDialog.launch(name, "", function() {
                    self.thank(ajax.jsonRpc($(e.target).data("action"), 'call', {
                        sign: ((signature)? signature.substr(signature.indexOf(",")+1) : false),
                    }));
                });
            });
        },

        thank: function(def) {
            if(def === undefined) def = (new $.Deferred()).resolve();

            this.thankYouDialog.$el.modal('show');
            return $.when(def);
        }
    });

    /* ----------------- */
    /*  Initializations  */
    /* ----------------- */
    website.add_template_file('/website_sign/static/src/xml/website_sign.xml');
    website.if_dom_contains('#o_sign_is_website_sign_page', function() {
        website.ready().then(function() {
            websiteSign = new CLASSES.WebsiteSign();

            var websiteSignPage = new WIDGETS.WebsiteSignPage(null, $('body'));
            websiteSign.signatureDialog = new WIDGETS.SignatureDialog(websiteSignPage, $('#o_sign_signer_name_input_info').val());

            /* ------------- */
            /*  Geolocation  */
            /* ------------- */
            var askLocationURL = $('#o_sign_ask_location_input').val();
            if(askLocationURL && navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    ajax.jsonRpc(askLocationURL, 'call', {
                        'latitude': position.coords.latitude,
                        'longitude': position.coords.longitude
                    });
                });
            }

            return websiteSignPage.start().then(function() {
                return websiteSign.signatureDialog.appendTo(websiteSignPage.$el);
            });
        });
    });
})();
