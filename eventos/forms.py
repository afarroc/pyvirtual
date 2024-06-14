from django import forms
from django.contrib.auth.models import User
from .models import Task, Event, Profile, Experience, Education, Skill, Status

class CreateNewEvent(forms.ModelForm):
    attendee = forms.ModelChoiceField(queryset=User.objects.all())
    assigned_to = forms.ModelChoiceField(queryset=User.objects.all())
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_status', 'host', 'attendee',
                   'assigned_to']

class AssignAttendeesForm(forms.Form):
    attendees = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class CreateNewTask(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'important', 'project']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
        }

class CreateNewProject(forms.Form):
    name = forms.CharField(label="Nombre del proyecto", max_length=200, widget=forms.TextInput(attrs={'class':'input'}))

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_status', 'venue', 'host', 'event_category', 'max_attendees', 'ticket_price']

class EventEditForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_status']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'location', 'profile_picture', 'linkedin_url']

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['job_title', 'company_name', 'start_date', 'end_date', 'description']

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if not start_date:
            raise forms.ValidationError("Start date is required.")
        return start_date

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['institution_name', 'degree', 'field_of_study', 'start_date', 'end_date', 'description']

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['skill_name', 'proficiency_level']

class EditStatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['status_name', 'icon', 'active', 'color']
