from django.shortcuts import render, redirect
from .models import  Metadata, AuditLog
from .forms import MetadataForm, UserLoginForm, UploadFileForm
from django.contrib.auth import authenticate, login, get_user_model
import pandas as pd
from google.cloud import bigquery
from sdv.metadata import SingleTableMetadata,  MultiTableMetadata
from django.contrib import messages
from sdv.single_table import GaussianCopulaSynthesizer
from sdv.multi_table import HMASynthesizer
import json
from django.contrib.auth import logout

from django.contrib.auth.models import User
from django.core.mail import send_mail
import random
def home(request):
    return render(request, 'generator/home.html')

def logout_view(request):
    # Logs out the user
    return redirect('generator:home')


def custom_logout(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('generator:home')  # Correctly redirecting to home page.
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    
    return render(request, 'generator/login.html', {'form': form})

def generate_metadata(request):
    if request.method == 'POST':
        form = MetadataForm(request.POST)
        if form.is_valid():
            table_name = form.cleaned_data['table_name']
            data_limit = form.cleaned_data['data_limit']
            metadata_choice = form.cleaned_data['metadata_choice']

            # Query BigQuery to get the data.
            client = bigquery.Client()
            sql_query = f"SELECT * FROM `{table_name}` LIMIT {data_limit}"
            df = client.query(sql_query).to_dataframe()

            # Generate metadata based on the table structure.
            metadata = SingleTableMetadata()
            metadata.detect_from_dataframe(df)
            metadata_json = metadata.to_json()

            # Save metadata to database.
            Metadata.objects.create(table_name=table_name, metadata_json=metadata_json)

            # Log the action.
            AuditLog.objects.create(user=request.user, action=f'Metadata generated for {table_name}')

            return redirect('home')
    else:
        form = MetadataForm()

    return render(request, 'generator/generate_metadata.html', {'form': form})

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            
            # Determine the appropriate engine based on file extension
            if uploaded_file.name.endswith('.xlsx'):
                engine = 'openpyxl'
            elif uploaded_file.name.endswith('.xls'):
                engine = 'xlrd'
            else:
                return render(request, 'generator/upload.html', {
                    'form': form,
                    'error': 'Invalid file type. Please upload an Excel (.xls or .xlsx) file.'
                })

            try:
                # Read the uploaded Excel file into a DataFrame
                df = pd.read_excel(uploaded_file, engine=engine)
            except ValueError as e:
                return render(request, 'generator/upload.html', {
                    'form': form,
                    'error': f'Error reading the Excel file: {str(e)}'
                })

            num_rows = int(request.POST.get('num_rows', 10))
            metadata_dict = {}

            # Loop through each column and determine its type and additional attributes
            for column in df.columns:
                if pd.api.types.is_numeric_dtype(df[column]):
                    representation = "Int64" if pd.api.types.is_integer_dtype(df[column]) else "Float"
                    metadata_dict[column] = {
                        "sdtype": "numerical",
                        "computer_representation": representation
                    }
                elif pd.api.types.is_string_dtype(df[column]):
                    metadata_dict[column] = {
                        "sdtype": "categorical",
                        "regex_format": "[A-Za-z0-9]+"
                    }
                elif pd.api.types.is_datetime64_any_dtype(df[column]):
                    metadata_dict[column] = {
                        "sdtype": "datetime",
                        "computer_representation": "datetime64[ns]"
                    }
                else:
                    metadata_dict[column] = {
                        "sdtype": "unknown"
                    }

            # Create an instance of SingleTableMetadata and detect from DataFrame
            metadata = SingleTableMetadata()  # Create an instance of SingleTableMetadata
            metadata.detect_from_dataframe(df)  # Use detect_from_dataframe from SingleTableMetadata

            # Create and fit the synthesizer using the original DataFrame
            synthesizer = GaussianCopulaSynthesizer(metadata)
            synthesizer.fit(df)

            # Now sample synthetic data based on user input
            synthetic_data = synthesizer.sample(num_rows=num_rows)

            # Convert metadata dictionary to JSON for rendering or further processing
            metadata_json = json.dumps(metadata_dict, indent=4)

            # Render results page with original and synthetic data
            return render(request, 'generator/results.html', {
                'original_data': df.to_html(),
                'synthetic_data': synthetic_data.to_html(),
                'metadata_json': metadata_json,
                'success_message': 'File processed successfully!'
            })
    else:
        form = UploadFileForm()

    return render(request, 'generator/upload.html', {'form': form})


User = get_user_model()  # Get the custom user model dynamically

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        # Check if the email exists
        try:
            user = User.objects.get(email=email)
            otp = random.randint(100000, 999999)  # Generate OTP
            request.session['otp'] = otp  # Store OTP in session
            request.session['email'] = email  # Store email in session

            # Send OTP via email (configure your email settings first)
            send_mail(
                'Your OTP Code',
                f'Your OTP code is {otp}',
                'admin@gmail.com',
                [email],
                fail_silently=False,
            )
            return redirect('generator:verify_otp')
        except User.DoesNotExist:
            return render(request, 'generator/forgot_password.html', {'error': 'Email not found.'})

    return render(request, 'generator/forgot_password.html')

# View for OTP Verification
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST['otp']
        # Check if entered OTP matches the one stored in session
        if str(entered_otp) == str(request.session.get('otp')):
            # If OTP matches, display success message
            return render(request, 'generator/verify_otp.html', {
                'success_message': 'Your OTP verification has been successfully completed.',
                'redirect_link': 'generator:password_reset'  # Pass the URL to redirect to password_rest page
            })
        else:
            # If OTP is invalid, return an error message
            return render(request, 'generator/verify_otp.html', {'error': 'Invalid OTP.'})
    
    return render(request, 'generator/verify_otp.html')

# View for Password Reset
def password_reset(request):
    if request.method == 'POST':
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']
        email = request.session.get('email')  # The email should be stored in the session after OTP verification
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match. Please try again.')
            return render(request, 'generator/password_reset.html')
        
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)  # Set the new password
            user.save()
            messages.success(request, 'Your password has been successfully reset.')
            return redirect('generator:login')  # Redirect to the login page after successful reset
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return render(request, 'generator/password_reset.html')

    return render(request, 'generator/password_reset.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        
        # Check if the username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('generator:register')

        # Check if the email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('generator:register')

        # Create a new user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        
        messages.success(request, 'Registration successful! You can now log in.')
        return redirect('generator:login')  # Redirect to login page after registration

    return render(request, 'generator/register.html')

def manage_users(request):
    if request.method == 'POST':
        email_to_delete = request.POST.get('email')
        try:
            user = User.objects.get(email=email_to_delete)
            user.delete()
            messages.success(request, f'User with email {email_to_delete} has been deleted.')
        except User.DoesNotExist:
            messages.error(request, 'Email not found.')

    # Retrieve all users
    users = User.objects.all()
    return render(request, 'generator/manage_users.html', {'users': users})


