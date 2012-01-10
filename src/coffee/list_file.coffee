class ModalLauncher
    constructor: (@el) ->

    launch: =>
        $('#modal-form').modal
            backdrop: true
            keyboard: true

$ ->
    $('.launch-modal')
        .each ->
            modal_launcher = new ModalLauncher @
            $(@).click modal_launcher.launch
