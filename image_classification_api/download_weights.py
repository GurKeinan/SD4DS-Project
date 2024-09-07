from torchvision import models
from torchvision.models import ResNet50_Weights

# Load and download the model weights
model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
