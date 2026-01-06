from rest_framework import serializers
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Location, Work, Education, Friendship, ExtraEmail, ExtraPhoneNumber
from django.db.models import Q

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'created_at', 'updated_at']

class WorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = ['id', 'company', 'position', 'description', 'created_at', 'updated_at']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'collage', 'subject', 'description', 'created_at', 'updated_at']

class ExtraEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraEmail
        fields = ['id', 'email', 'is_verified', 'created_at']

class ExtraPhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraPhoneNumber
        fields = ['id', 'phone_number', 'is_verified', 'created_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'profile_name', 'phone_number', 'password', 'gender', 'date_of_birth', 'share_data']

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            profile_name=validated_data['profile_name'],
            phone_number=validated_data.get('phone_number', ''),
            gender=validated_data.get('gender', ''),
            date_of_birth=validated_data.get('date_of_birth', None),
            share_data=validated_data.get('share_data', False)
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
        else:
            raise serializers.ValidationError('Must include "email" and "password".')

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    locations = LocationSerializer(many=True, read_only=True)
    works = WorkSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    extra_emails = ExtraEmailSerializer(many=True, read_only=True)
    extra_phone_numbers = ExtraPhoneNumberSerializer(many=True, read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    post_count = serializers.IntegerField(source='posts.count', read_only=True)
    friends_count = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(source='post_likes.count', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'profile_name', 'description', 'profile_image', 'cover_photo',
                  'website', 'phone_number', 'gender', 'date_of_birth', 'profile_lock',
                  'date_joined', 'locations', 'works', 'educations', 'extra_emails', 'extra_phone_numbers',
                  'post_count', 'friends_count', 'likes_count', 'stripe_account_id', 'is_onboarding_completed']
        read_only_fields = ['id', 'date_joined', 'post_count', 'friends_count', 'likes_count', 'stripe_account_id', 'is_onboarding_completed']
    
    
    def to_representation(self, instance):
        """Override to use profile_image_url as profile_image in response"""
        representation = super().to_representation(instance)
        return representation

    def get_friends_count(self, obj):
        return Friendship.objects.filter(
            (Q(receiver=obj) | Q(requester=obj)) & Q(status='accepted')
        ).count()

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'profile_name', 'profile_image', 'profile_lock']
    

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)

class ChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False)

class ChangePhoneNumberSerializer(serializers.Serializer):
    new_phone_number = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False)

class AddEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False)

class AddPhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True, required=True)
    code = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
