from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from ..models import Ingredient, Stock, StockTransaction
from ..forms import IngredientForm, StockTransactionForm

@login_required
def ingredient_list(request):
    ingredients = Ingredient.objects.all()
    return render(request, 'stock/ingredient_list.html', {'ingredients': ingredients})

@login_required
def ingredient_create(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save()
            # Create initial stock record
            Stock.objects.create(
                ingredient=ingredient,
                current_quantity=0,
                alert_threshold=ingredient.minimum_quantity
            )
            messages.success(request, 'Ingredient added successfully.')
            return redirect('ingredient_list')
    else:
        form = IngredientForm()
    return render(request, 'stock/ingredient_form.html', {'form': form, 'title': 'Add Ingredient'})

@login_required
def ingredient_update(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingredient updated successfully.')
            return redirect('ingredient_list')
    else:
        form = IngredientForm(instance=ingredient)
    return render(request, 'stock/ingredient_form.html', {'form': form, 'title': 'Edit Ingredient'})

@login_required
def stock_update(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    stock = get_object_or_404(Stock, ingredient=ingredient)
    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.ingredient = ingredient
            transaction.created_by = request.user
            transaction.save()
            messages.success(request, 'Stock updated successfully.')
            return redirect('ingredient_list')
    else:
        form = StockTransactionForm()
    return render(request, 'stock/stock_form.html', {
        'form': form,
        'ingredient': ingredient,
        'stock': stock,
        'title': 'Update Stock'
    })

@login_required
def stock_transaction_create(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.ingredient = ingredient
            transaction.created_by = request.user
            transaction.save()
            messages.success(request, 'Stock transaction recorded successfully.')
            return redirect('ingredient_list')
    else:
        form = StockTransactionForm()
    return render(request, 'stock/transaction_form.html', {
        'form': form,
        'ingredient': ingredient,
        'title': 'Add Stock'
    })

@login_required
def stock_transaction_list(request):
    transactions = StockTransaction.objects.all().order_by('-created_at')
    return render(request, 'stock/transaction_list.html', {'transactions': transactions}) 