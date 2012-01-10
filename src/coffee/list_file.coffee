class ModalLauncher
    constructor: (@el) ->

    launch: =>
        record = $(@el).parents('[data-file-key]').first()[0]
        file_info = JSON.parse record.dataset.fileInfo
        $('#modal-form')
            .find('.file-name')
                .empty()
                .append(file_info.path)
                .end()
            .find('.file-netprint_id')
                .empty()
                .append(file_info.netprint_id)
                .end()
            .modal
                backdrop: true
                keyboard: true
                show: true

update_file_list = ->
    target = $('#list-file')
    target.empty()
    if _.isEmpty data
        $('<p>登録済みファイルはありません。</p>')
            .appendTo(target)
    else
        tbody = $('<tbody></tbody>')
        $('<table class="zebra-striped"></table>')
            .append('<thead><tr><th>ファイル</th><th>予約番号</th><th></th></tr></thead>')
            .append(tbody)
            .appendTo(target)
        for file_info in data
            update_file_record tbody, file_info

update_file_record = (tbody, file_info) ->
    tr = $('<tr data-file-key="" data-file-info=""></tr>')
        .append("<td>#{file_info.path}</td>")
        .append("<td>#{file_info.netprint_id}</td>")
        .append('<td><a class="btn launch-modal">詳細</a></td>')
        .appendTo(tbody)
    tr_el = tr[0]
    tr_el.dataset.fileKey = file_info.key
    tr_el.dataset.fileInfo = JSON.stringify file_info

$ ->
    update_file_list()
    $('.launch-modal')
        .each ->
            modal_launcher = new ModalLauncher @
            $(@).click modal_launcher.launch
