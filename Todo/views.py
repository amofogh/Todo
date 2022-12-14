from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.core.validators import validate_email

import requests

from .models import *
from .auth_methods import convert_to_hash


# Create your views here.

def Todo_todo(request):
    if not request.session.get('login'):
        return redirect(reverse('Todo:login'))
    context = {}

    try:
        member = Member.objects.get(id=request.session.get('id'))
        context.update({'user': member})

        user_tasks = Task.objects.filter(user=member)
        context.update({'tasks': user_tasks})
    except Member.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'user not found please login again')
        return redirect(reverse('Todo:login'))
    return render(request, 'Todo.html', context)


def Todo_login(request):
    if not request.session.get('login'):

        context = {
            'site_key': settings.RECAPTCHA_SITE_KEY,
        }

        if request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            remember = request.POST.get('remember')

            # captcha verification
            secret_key = settings.RECAPTCHA_SECRET_KEY
            data = {
                'response': request.POST.get('g-recaptcha-response'),
                'secret': secret_key
            }
            resp = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            result_json = resp.json()
            # end captcha verification

            if not result_json.get('success'):
                if result_json.get('error-codes')[0] == 'timeout-or-duplicate':
                    messages.add_message(request, messages.ERROR, 'Timeout try again')
                else:
                    messages.add_message(request, messages.ERROR, 'Captcha error please try again')
            else:
                password = convert_to_hash(password)

                try:
                    member = Member.objects.get(username=username)
                    if password == member.password:
                        request.session['login'] = True
                        request.session['id'] = member.id
                        request.session.set_expiry(0)
                        if remember:
                            request.session.set_expiry(48 * 60 * 60)

                        return redirect(reverse('Todo:todo'))
                    else:
                        request.session['login'] = False
                        request.session['id'] = None
                        messages.add_message(request, messages.ERROR, 'Password is incorrect')

                except Member.DoesNotExist:
                    messages.add_message(request, messages.ERROR, 'User does not exist')

        return render(request, 'login.html', context)
    else:
        return redirect(reverse('Todo:todo'))


def Todo_register(request):
    context = {}
    if not request.session.get('login'):

        if request.POST:
            name = request.POST.get('name')
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            re_password = request.POST.get('re_password')

            try:
                validate_email(email)
            except ValidationError:
                messages.add_message(request, messages.ERROR, 'Email is not valid please write valid email')

            if password == re_password:
                try:
                    Member.objects.get(username__iexact=username)
                    messages.add_message(request, messages.ERROR, 'Username exists please choose another one')
                except Member.DoesNotExist:
                    try:
                        Member.objects.get(email__iexact=email)
                        messages.add_message(request, messages.ERROR, 'Email exists please choose another one')
                    except Member.DoesNotExist:
                        password = convert_to_hash(password)
                        member = Member.objects.create(name=name, username=username, email=email, password=password)
                        messages.add_message(request, messages.SUCCESS, f'{username} has been created')
                        request.session['login'] = True
                        request.session['id'] = member.id
                        return redirect(reverse('Todo:todo'))
            else:
                messages.add_message(request, messages.ERROR, 'Passwords does not match')

        return render(request, 'register.html', context)
    else:
        return redirect(reverse('Todo:todo'))


def Todo_logout(request):
    request.session['login'] = False
    request.session['id'] = None

    return redirect(reverse('Todo:login'))


def Todo_add_task(request):
    if not request.session.get('login'):
        return redirect(reverse('Todo:login'))

    if request.POST:
        user_id = request.session.get('id')
        text = request.POST.get('text')
        priority = request.POST.get('priority')
        if priority:
            try:
                user = Member.objects.get(id=user_id)
            except Member.DoesNotExist:
                return JsonResponse({"error": 'User not found please login again'}, status=400)
            new_task = Task.objects.create(user=user, text=text, priority=priority)
            return JsonResponse({"message": 'Task added successfully', "task_id": new_task.id,
                                 'task_date': f'{new_task.date.year}/{new_task.date.month}/{new_task.date.day}',
                                 'task_time': f'{new_task.date.hour}:{new_task.date.minute}', }, status=200)
        else:
            return JsonResponse({"error": 'Fill the priority field please'}, status=400)

    return JsonResponse({"error": 'Task failed please try again'}, status=400)


def Todo_check_Task(request):
    if not request.session.get('login'):
        return redirect(reverse('Todo:login'))

    if request.POST:
        status = request.POST.get('status')
        task_id = request.POST.get('task_id')

        try:
            task = Task.objects.get(id=task_id)
            if status == 'false':
                status = False
            task.done = bool(status)
            task.save()
            messages.add_message(request, messages.SUCCESS, 'Task updated successfully')
            return JsonResponse({"message": 'Task updated successfully'}, status=200)

        except Task.DoesNotExist:
            return JsonResponse({"error": 'Task Not FOund'}, status=404)


def Todo_edit_task(request):
    if not request.session.get('login'):
        return redirect(reverse('Todo:login'))

    if request.POST:
        task_id = request.POST.get('task_id')
        text = request.POST.get('text')
        priority = request.POST.get('priority')

        try:
            task = Task.objects.get(id=task_id)
            task.text = text
            task.priority = priority
            task.save()
            messages.add_message(request, messages.SUCCESS, 'Task edited successfully')

        except Task.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Task Not FOund')
