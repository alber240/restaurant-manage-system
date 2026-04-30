from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from restaurant.forms import CustomUserCreationForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Login the user immediately
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Gourmet House!')
            return redirect('menu')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})