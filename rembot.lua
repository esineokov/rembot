box.cfg{
    listen=3301,
    log_level=7,
    log='/tmp/tnt_rembot.log'
}

box.schema.user.grant('guest', 'read,write,execute,drop', 'universe', nil, {if_not_exists=true})


box.once("create_v0.0.4", function()

    box.schema.space.create('users', {
        if_not_exists = true,
        format={
            {name = 'user_id', type = 'string'},
            {name = 'time_zone', type = 'string'},
         }
    })

    box.space.users:create_index('user_id', {
        type = 'tree',
        parts = {{1, 'string'}},
        if_not_exists = true,
        unique=true
    })

    box.schema.space.create('chats', {
        if_not_exists = true,
        format={
            {name = 'chat_id', type = 'string'},
            {name = 'time_zone', type = 'string'},
         }
    })

    box.space.chats:create_index('chat_id', {
        type = 'tree',
        parts = {{1, 'string'}},
        if_not_exists = true,
        unique=true
    })

    box.schema.space.create('notes', {
        if_not_exists = true,
        format={
            {name = 'user_id', type = 'string'},
            {name = 'chat_id', type = 'string'},
            {name = 'msg_id', type = 'string'},
            {name = 'timestamp', type = 'integer'}
         }
    })

    box.space.notes:create_index('uniq', {
        type = 'tree',
        parts = {{1, 'string'}, {2, 'string'}, {3, 'string'}},
        if_not_exists = true,
        unique=true
    })

    box.space.notes:create_index('chat_id', {
        type = 'tree',
        parts = {{2, 'string'}},
        if_not_exists = true,
        unique=false
    })

    box.space.notes:create_index('user_chat', {
        type = 'tree',
        parts = {{1, 'string'},{2, 'string'}},
        if_not_exists = true,
        unique=false
    })

end
)
