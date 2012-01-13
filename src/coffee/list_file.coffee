class ModalLauncher
    constructor: (@el, @apply_callback) ->

    launch: =>
        file_info = get_stored_data @el
        pin = str_pin file_info.pin
        form = $('#modal-form')
        form.find('.file-name').text file_info.path
        form.find('.file-netprint_id').text file_info.netprint_id
        form.find("[type=radio][value=#{pin}]")
            .attr('checked', 'checked')
        form.find('.apply')
            .unbind('click')
            .click(@handle_apply)
        form.find('.cancel')
            .unbind('click')
            .click(-> form.modal('hide'))
        form.modal
            backdrop: true
            keyboard: true
            show: true

    handle_apply: =>
        form = $('#modal-form')
        form.modal('hide')
        val =
            key: get_stored_key @el
            pin: form.find('[type=radio]:checked').val()
        @apply_callback val


get_stored_key = (el) ->
    $(el).parents('[data-file-key]').get(0)
         .dataset.fileKey


get_stored_data = (el) ->
    JSON.parse $(el)
        .parents('[data-file-key]').get(0)
        .dataset.fileInfo


update_file_list = ->
    target = $('#list-file')
    target.empty()
    if _.size(data) == 0
        $('<p>登録済みファイルはありません。</p>')
            .appendTo(target)
    else
        thead = $('<thead><tr><th>ファイル</th><th>ファイル名(ネットプリント)</th><th>予約番号</th><th>自動登録</th></tr></thead>')
        tbody = $('<tbody></tbody>')
        $('<table class="zebra-striped"></table>')
            .append(thead)
            .append(tbody)
            .appendTo(target)
        for file_info in data
            update_file_record tbody, file_info


str_pin = (pin) ->
    if pin
        'on'
    else
        'off'


update_file_record = (tbody, file_info) ->
    pin = str_pin file_info.pin
    result = tbody.find("tr[data-file-key=#{file_info.key}]")
    if _.size(result) == 0
        tr = $('<tr data-file-key="" data-file-info=""></tr>')
            .append("<td>#{file_info.path}</td>")
            .append("<td>#{file_info.netprint_name}</td>")
            .append("<td>#{file_info.netprint_id}</td>")
            .append("<td>#{pin}</td>")
            .append('<td><a class="btn launch-modal">詳細</a></td>')
            .appendTo(tbody)
            .get(0)
        tr.dataset.fileKey = file_info.key
    else
        result.find('td:eq(0)').text file_info.path
        result.find('td:eq(1)').text file_info.netprint_name
        result.find('td:eq(2)').text file_info.netprint_id
        result.find('td:eq(3)').text pin
        tr = result.get(0)
    tr.dataset.fileInfo = JSON.stringify file_info


sync_dropbox = ->
    request = JSON.stringify
        token: window.csrf_token

    callback = (data) ->
        console.debug data

    $.post window.sync_api_url
        , request
        , callback
        , 'json'


$ ->
    update_file_list()
    $('.launch-modal')
        .each ->
            modal_launcher = new ModalLauncher @, (val) ->
                request = JSON.stringify
                    pin: val.pin
                    file_key: val.key
                    token: window.csrf_token

                callback = (file_info) ->
                    tbody = $('#list-file tbody')
                    update_file_record tbody, file_info

                $.post window.pin_api_url
                    , request
                    , callback
                    , 'json'

            $(@).click modal_launcher.launch

    $('.sync_dropbox').click sync_dropbox
