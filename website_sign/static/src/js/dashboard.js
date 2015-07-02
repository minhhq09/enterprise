
odoo.define('website_sign.dashboard', function(require) {
    'use strict';

    var session = require('web.session');
    var Widget = require('web.Widget');
    var website = require('website.website');
    
    var WIDGETS = {};

    WIDGETS.DashboardRow = Widget.extend({
        events: {
            'click .sign_dashboard_title_nav button': function(e) {
                if(e.target === this.$el.find('.sign_dashboard_title_nav button').first()[0])
                    this.page--;
                else
                    this.page++;

                this.refresh();
            },

            'click .sign_dashboard_item .archive_button': function(e) {
                var self = this;

                session.rpc("/sign/archive/" + $(e.target).data('ref'), {
                    'value': !$(e.target).closest('.sign_dashboard_item').data('archived')
                }).then(function (value) {
                    $(e.target).closest('.sign_dashboard_item').data('archived', +value);
                    self.refresh();
                });
                return false;
            },

            'click .sign_dashboard_item .favorite_button': function(e) {
                var self = this;

                session.rpc("/sign/favorite/" + $(e.target).data('ref'), {
                    'value': !$(e.target).closest('.sign_dashboard_item').data('favorited')
                }).then(function (value) {
                    $(e.target).closest('.sign_dashboard_item').data('favorited', +value);
                    self.refresh();
                });
                return false;
            },
        },

        init: function(parent, $root, tCorrect) {
            this._super(parent);
            this.setElement($root);

            this.showArchives = false;
            this.showOnlyFavorites = false;

            this.page = 0;
            this.maxPage = 0;
            this.tCorrect = tCorrect;
        },

        start: function() {
            this.$items = this.$('.sign_dashboard_item');
            this.$buttons = this.$('.sign_dashboard_title_nav').first().find('button');
            this.$pageCounter = this.$('.sign_dashboard_title_nav').first().find('.page_counter');
            this.$pageTotalCounter = this.$('.sign_dashboard_title_nav').first().find('.page_total_counter');

            this.$items.each(function(i, el) {
                $(el).data('default_order', i);
            });

            return this._super();
        },

        refresh: function(showArchives, showOnlyFavorites, sort) {
            var self = this;

            self.showArchives = (showArchives === undefined)? self.showArchives : showArchives;
            self.showOnlyFavorites = (showOnlyFavorites === undefined)? self.showOnlyFavorites : showOnlyFavorites;

            var count = self.$items.filter(function(i, el) {
                return (($(el).data('favorited') || !self.showOnlyFavorites) && (!$(el).data('archived') || self.showArchives));
            }).length - self.tCorrect;

            if(self.$items.length <= 0)
                self.$buttons.prop('disabled', true);
            else
            {
                self.$buttons.prop('disabled', false);

                self.maxPage = ~~(Math.max(0, count-1)/(6-self.tCorrect));
                self.page = Math.min(self.page, self.maxPage);

                if(self.page <= 0) {
                    self.page = 0;
                    self.$buttons.eq(0).prop('disabled', true);
                }
                if(self.page >= self.maxPage) {
                    self.page = self.maxPage;
                    self.$buttons.eq(1).prop('disabled', true);
                }

                self.$buttons.closest('.sign_dashboard_title_nav').css('visibility', (self.maxPage > 0)? 'visible' : 'hidden');
            }

            self.$pageCounter.html("" + Math.min(count, (self.page+1)*(6-self.tCorrect)));
            self.$pageTotalCounter.html("" + count);

            self.$el.hide();

            if(sort) {
                self.$items = self.$items.sort(function(a, b) {
                    var aFav = parseInt($(a).data('favorited')), bFav = parseInt($(b).data('favorited'));
                    if(aFav !== bFav)
                        return ((aFav)? -1 : 1);

                    var aArch = parseInt($(a).data('archived')), bArch = parseInt($(b).data('archived'));
                    if(aArch !== bArch)
                        return ((aArch)? 1 : -1);

                    return (parseInt($(a).data('default_order')) - parseInt($(b).data('default_order')));
                });
            }
            self.$el.find('h4').next().append(self.$items.detach());

            var aCorrect = 0;
            for(var i = 0 ; i < self.$items.length ; i++) {
                if(self.$items.eq(i).data('archived')) {
                    if(!self.showArchives) {
                        aCorrect++;
                        self.$items.eq(i).hide();
                        continue;
                    }
                    self.$items.eq(i).addClass('archived');
                }
                else
                    self.$items.eq(i).removeClass('archived');

                if(self.$items.eq(i).data('favorited')) {
                    self.$items.eq(i).find('.favorite_button').prop('title', "Unmark as Favorite");
                    self.$items.eq(i).find('.favorite_button').removeClass('fa-star-o').addClass('fa-star');
                    self.$items.eq(i).addClass('favorited');
                }
                else {
                    self.$items.eq(i).find('.favorite_button').prop('title', "Mark as Favorite");
                    self.$items.eq(i).find('.favorite_button').removeClass('fa-star').addClass('fa-star-o');
                    self.$items.eq(i).removeClass('favorited');
                }

                if((~~((i-self.tCorrect-aCorrect)/(6-self.tCorrect)) === self.page || (self.tCorrect && i === 0)) && (self.$items.eq(i).data('favorited') || !self.showOnlyFavorites)) {
                    self.$items.eq(i).show();
                    self.$el.show();
                }
                else
                    self.$items.eq(i).hide();
            }
        },
    });

    WIDGETS.Dashboard = Widget.extend({
        events: {
            'change #show_archives_toggle': function(e) {
                this.showArchives = $(e.target).prop('checked');
                this.refresh(true);

                session.rpc("/sign/set_toggles", {
                    'object': 'archive',
                    'value': this.showArchives
                });
            },

            'change #show_favorites_toggle': function(e) {
                this.showOnlyFavorites = $(e.target).prop('checked');
                this.refresh(true);

                session.rpc("/sign/set_toggles", {
                    'object': 'favorite',
                    'value': this.showOnlyFavorites
                });
            },

            'change input[type="file"]': function(e) {
                var f = e.target.files[0];
                var reader = new FileReader();

                reader.onload = function(e) {
                    session.rpc("/sign/new_template", {
                        'name': f.name,
                        'dataURL': e.target.result
                    }).then(function(data) {
                        window.location.href = "/sign/template/" + data.template;
                    });
                };
                reader.readAsDataURL(f);
            },

            'click #upload_template_button': function(e) {
                this.$el.find('input[type="file"]').click();
            },
        },

        init: function(parent, $root) {
            this._super(parent);
            this.setElement($root);
        },

        start: function() {
            var self = this;

            self.showArchives = self.$('#show_archives_toggle').prop('checked');
            self.showOnlyFavorites = self.$('#show_favorites_toggle').prop('checked');
            self.dashboardRows = [];

            var waitFor = [];

            self.$('.sign_dashboard_row').each(function(i, row) {
                var row = new WIDGETS.DashboardRow(self, $(row), ((i === 0)? 1 : 0));
                waitFor.push(row.start());
                self.dashboardRows.push(row);
            });

            var $newTemplateInput = $("<input type='file' name='files[]'/>");
            self.$('#upload_template_button').after($newTemplateInput);
            $newTemplateInput.hide();

            return $.when(self._super(), $.when.apply($, waitFor).then(function() {
                self.refresh(true);
            }));
        },

        refresh: function(sort) {
            for(var i = 0 ; i < this.dashboardRows.length ; i++)
                this.dashboardRows[i].refresh(this.showArchives, this.showOnlyFavorites, sort);
        },
    });
    
    website.if_dom_contains('#sign_dashboard', function(dashboardDOM) {
        website.ready().then(function() {
            var dashboard = new WIDGETS.Dashboard(null, dashboardDOM);
            return dashboard.start();
        });
    });
        
    return WIDGETS;
});
