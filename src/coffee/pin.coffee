class Pin
    constructor: (@el) ->

    toggle: =>
        pin_state = if @el.dataset.netprintPin == "on"
                         "off"
                     else
                         "on"

        request_data = JSON.stringify
            pin: pin_state
            file_key: @el.dataset.netprintKey

        callback = (data) =>
            @el.dataset.netprintPin = data.pin
            @update_face()

        $.post window.pin_api_url, request_data, callback, 'json'

    update_face: =>
        # Because default icon value is arrow-r, to appear the plus icon, remove the class first.
        # XXX define custom icon, likes pin.
        if @el.dataset.netprintPin == "on"
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
