from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required, permission_required
from apps.frms.models import NewEmployee
from apps.frms.forms.new_employee import NewEmployeeForm
from apps.workflow.views.permissions import has_model_permission

@login_required
def new_employee(request):
    # static “add” check in your system
    if not has_model_permission(request.user, NewEmployee, 'add'):
        raise PermissionDenied

    if request.method == 'POST':
        form = NewEmployeeForm(request.POST, user=request.user)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.submitted_by = request.user
            emp.save()

            return redirect('new_employee_list')   # or wherever you like
    else:
        form = NewEmployeeForm(user=request.user)

    return render(request, 'new_employee.html', {
        'form': form
    })

@login_required
def new_employee_list(request):
    employees = NewEmployee.objects.filter(submitted_by=request.user)
    context = {'employees': employees}

    return render(request, 'new_employee_list.html', context)

@login_required
def new_employee_detail(request, pk):
    employee = get_object_or_404(NewEmployee, pk=pk)

    if not has_model_permission(request.user, NewEmployee, 'view'):
        raise PermissionDenied

    # Handle an edit‐form submission
    if request.method == "POST" and "update_new_employee" in request.POST:
        # Enforce per‐status edit rights
        if not employee.can_edit(request.user):
            raise PermissionDenied("You may not edit this record in its current status.")

        form = NewEmployeeForm(
            request.POST,
            instance = employee,
            user = request.user,
            exclude_workflow = True
        )
        if form.is_valid():
            form.save()
            return redirect("new_employee_detail", pk=employee.pk)
    else:
        form = NewEmployeeForm(
            instance = employee,
            user = request.user,
            exclude_workflow = True
        )

    # Always load transitions for the transition widget
    transitions = employee.get_available_transitions(request.user)

    return render(request, "new_employee_detail.html", {
        "employee":    employee,
        "form":        form,
        "can_edit":    employee.can_edit(request.user),
        "transitions": transitions,
    })