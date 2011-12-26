class Pin
    constructor: (@el) ->

    toggle: =>
        console.debug @el.dataset.netprintId, @el.dataset.pin
        $.post 'http://localhost:8080/pin'
            , JSON.stringify(
                'pin': if @el.dataset.pin == "on"
                            "off"
                       else
                            "on"
                'file_info_key': 'ahVkZXZ-bmV0cHJpbnRib3gtYWxwaGFyJgsSC0Ryb3Bib3hVc2VyGAEMCxIPRHJvcGJveEZpbGVJbmZvGAgM')
            , (data, status) =>
                if status == "success"
                    @el.dataset.pin = JSON.parse(data).pin
                    @update_face()

    update_face: =>
        # Because default icon value is arrow-r, to appear the plus icon, remove the class first.
        # XXX define custom icon, likes pin.
        if @el.dataset.pin == "on"
            $(@el).find('.ui-icon')
                .removeClass("ui-icon-arrow-r")
                .addClass("ui-icon-star")
        else
            $(@el).find('.ui-icon')
                .removeClass("ui-icon-arrow-r")
                .removeClass("ui-icon-star")


$('#top').live 'pageinit'
    , ->
        $('.pin_control')
            .each ->
                pin = new Pin @
                $(@).click pin.toggle
                pin.update_face()
