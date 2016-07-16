import json
import logging

from django.conf import settings
from django.contrib import auth
from django.core.signing import TimestampSigner
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound, HttpResponseNotAllowed
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt


logger = logging.getLogger(__name__)
signer = TimestampSigner()


@csrf_exempt
def botapi(request, token):
    if token != settings.TGAUTH_TOKEN:
        return HttpResponseNotFound()
    if request.method == 'POST':
        update = json.loads(request.body.decode(request.encoding))
        if 'message' in update and update['message']['text'] in COMMANDS:
            return COMMANDS[update['message']['text']](request, update)
        else:
            return JsonResponse({
                'method': 'sendMessage',
                'chat_id': update['chat']['id'],
                'text': 'No such command',
            })
    else:
        return HttpResponseNotAllowed()


def login_cmd(request, update):

    msg = update['message']

    if 'from' not in msg:
        logger.error("Got message from without 'from'!")
        return JsonResponse({
            'method': 'sendMessage',
            'chat_id': update['chat']['id'],
            'text': 'Что-то пошло не так, боту пришло сообщение из группы.',
        })

    user_info = msg['from']

    if msg['type'] != 'private':
        return JsonResponse({
            'method': 'sendMessage',
            'chat_id': update['chat']['id'],
            'text': 'Эта команда должна быть отправлена личным сообщением, '
                    'а не публично в группе.',
        })

    user, created = auth.get_user_model().get_or_create(username=user_info['username'])

    reply = []

    if created:

        user.first_name = user_info['first_name']
        user.last_name = user_info.get('last_name')

        password = auth.get_user_model().objects.make_random_password()
        user.set_password(password)

        user.save()

        reply.append("Добро пожаловать в Sunsurfers Map! :pray:")
        reply.append("Для тебя создан новый аккаунт:")
        reply.append("Логин - %s" % user.username)
        reply.append("Пароль - %s" % password)
        reply.append("")

    reply.append("Ссылка для входа на сайт (действует 10 минут): %s" % reverse(
        ".login", args=signer.sign()
    ))

    return JsonResponse({
        'method': 'sendMessage',
        'chat_id': update['chat']['id'],
        'text': '\n'.join(reply),
    })


COMMANDS = {
    '/login': login_cmd,
}


def login(request, data):
    user_id = signer.unsign(data, max_age=600)
    auth.login(request, auth.get_user_model().objects.get(id=user_id))
    return redirect('map')