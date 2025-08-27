from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.contrib.auth.models import User

from .models import Category, Task, TaskAttachment
from .serializers import (
    UserRegistrationSerializer, CategorySerializer, 
    TaskSerializer, TaskListSerializer, TaskAttachmentSerializer
)

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TaskViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'priority', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'due_date', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        return TaskSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_stats(self, request):
        """Custom endpoint to get user task statistics"""
        tasks = self.get_queryset()
        stats = {
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(status='completed').count(),
            'pending_tasks': tasks.filter(status='pending').count(),
            'high_priority_tasks': tasks.filter(priority='high').count(),
        }
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Custom action to mark a task as completed"""
        task = self.get_object()
        task.status = 'completed'
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)

class TaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    
    def get_queryset(self):
        # Only show attachments for user's tasks
        return TaskAttachment.objects.filter(task__user=self.request.user)
    
    def perform_create(self, serializer):
        # Ensure the task belongs to the current user
        task_id = self.request.data.get('task')
        try:
            task = Task.objects.get(id=task_id, user=self.request.user)
            filename = self.request.data.get('file').name
            serializer.save(task=task, filename=filename)
        except Task.DoesNotExist:
            raise serializers.ValidationError("Task not found")
