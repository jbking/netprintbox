cache = window.applicationCache
if navigator.onLine and cache?
    $ ->
        $(cache).bind "updateready"
            , ->
                cache.swapCache()
        cache.update()
