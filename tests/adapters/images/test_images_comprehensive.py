"""Comprehensive tests for FastBlocks image adapters."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastblocks.adapters.images._base import ImagesBase
from fastblocks.adapters.images.cloudinary import (
    CloudinaryImages,
    CloudinaryImagesSettings,
)
from fastblocks.adapters.images.imagekit import ImageKitImages, ImageKitImagesSettings


@pytest.mark.unit
class TestImagesBase:
    """Test ImagesBase adapter functionality."""

    def test_images_base_inheritance(self):
        """Test ImagesBase inherits from correct base classes."""
        adapter = ImagesBase()
        assert hasattr(adapter, "MODULE_ID")
        assert hasattr(adapter, "MODULE_STATUS")
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_images_base_protocol_compliance(self):
        """Test ImagesBase implements ImagesProtocol."""
        # Check that required methods exist
        required_methods = ["get_img_tag", "get_image_url"]
        for method in required_methods:
            assert hasattr(ImagesBase, method)

    def test_images_base_abstract_methods(self):
        """Test abstract methods raise NotImplementedError."""
        adapter = ImagesBase()

        with pytest.raises(NotImplementedError):
            adapter.get_img_tag("test.jpg", "Test")

        with pytest.raises(NotImplementedError):
            adapter.get_image_url("test.jpg")


@pytest.mark.unit
class TestCloudinaryAdapter:
    """Test Cloudinary adapter functionality."""

    def test_cloudinary_adapter_initialization(self):
        """Test Cloudinary adapter initializes correctly."""
        adapter = CloudinaryImages()
        assert isinstance(adapter.settings, CloudinaryImagesSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_cloudinary_settings_defaults(self):
        """Test Cloudinary settings have correct defaults."""
        settings = CloudinaryImagesSettings()
        assert settings.secure is True
        assert settings.transformations == {}

    def test_cloudinary_img_tag_basic(self):
        """Test basic image tag generation."""
        adapter = CloudinaryImages()
        adapter.settings.cloud_name = "test-cloud"

        result = adapter.get_img_tag("test.jpg", "Test Image")

        assert (
            'src="https://res.cloudinary.com/test-cloud/image/upload/test.jpg"'
            in result
        )
        assert 'alt="Test Image"' in result
        assert "<img" in result

    def test_cloudinary_img_tag_with_attributes(self):
        """Test image tag with additional attributes."""
        adapter = CloudinaryImages()
        adapter.settings.cloud_name = "test-cloud"

        result = adapter.get_img_tag(
            "test.jpg", "Test Image", width=300, height=200, class_="responsive"
        )

        assert 'width="300"' in result
        assert 'height="200"' in result
        assert 'class="responsive"' in result

    @pytest.mark.asyncio
    async def test_cloudinary_get_image_url_basic(self):
        """Test basic image URL generation."""
        adapter = CloudinaryImages()
        adapter.settings.cloud_name = "test-cloud"

        url = await adapter.get_image_url("test.jpg")

        assert url == "https://res.cloudinary.com/test-cloud/image/upload/test.jpg"

    @pytest.mark.asyncio
    async def test_cloudinary_get_image_url_with_transformations(self):
        """Test image URL with transformations."""
        adapter = CloudinaryImages()
        adapter.settings.cloud_name = "test-cloud"

        url = await adapter.get_image_url(
            "test.jpg", width=300, height=200, crop="fill", quality="auto"
        )

        assert "test-cloud" in url
        assert "w_300" in url
        assert "h_200" in url
        assert "c_fill" in url
        assert "q_auto" in url

    @pytest.mark.asyncio
    async def test_cloudinary_upload_image(self):
        """Test image upload functionality."""
        adapter = CloudinaryImages()
        adapter.settings.cloud_name = "test-cloud"
        adapter.settings.api_key = "test-key"
        adapter.settings.api_secret = "test-secret"

        # Mock the cloudinary upload
        with patch("cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {
                "public_id": "uploaded_image",
                "secure_url": "https://res.cloudinary.com/test-cloud/image/upload/uploaded_image.jpg",
            }

            result = await adapter.upload_image(b"fake_image_data", "test.jpg")

            assert result["public_id"] == "uploaded_image"
            assert "secure_url" in result
            mock_upload.assert_called_once()

    def test_cloudinary_build_transformation_url(self):
        """Test transformation URL building."""
        adapter = CloudinaryImages()
        adapter.settings.cloud_name = "test-cloud"

        url = adapter._build_transformation_url(
            "test.jpg",
            {
                "width": 300,
                "height": 200,
                "crop": "fill",
                "quality": "auto",
                "format": "webp",
            },
        )

        assert "w_300" in url
        assert "h_200" in url
        assert "c_fill" in url
        assert "q_auto" in url
        assert "f_webp" in url

    def test_cloudinary_normalize_image_id(self):
        """Test image ID normalization."""
        adapter = CloudinaryImages()

        # Test various image ID formats
        assert adapter._normalize_image_id("folder/image.jpg") == "folder/image"
        assert adapter._normalize_image_id("image.png") == "image"
        assert adapter._normalize_image_id("no_extension") == "no_extension"


@pytest.mark.unit
class TestImageKitAdapter:
    """Test ImageKit adapter functionality."""

    def test_imagekit_adapter_initialization(self):
        """Test ImageKit adapter initializes correctly."""
        adapter = ImageKitImages()
        assert isinstance(adapter.settings, ImageKitImagesSettings)
        assert adapter.MODULE_STATUS == "stable"
        assert isinstance(adapter.MODULE_ID, UUID)

    def test_imagekit_settings_defaults(self):
        """Test ImageKit settings have correct defaults."""
        settings = ImageKitImagesSettings()
        assert settings.secure is True
        assert settings.transformations == {}

    def test_imagekit_img_tag_basic(self):
        """Test basic image tag generation."""
        adapter = ImageKitImages()
        adapter.settings.url_endpoint = "https://ik.imagekit.io/test"

        result = adapter.get_img_tag("test.jpg", "Test Image")

        assert 'src="https://ik.imagekit.io/test/test.jpg"' in result
        assert 'alt="Test Image"' in result
        assert "<img" in result

    @pytest.mark.asyncio
    async def test_imagekit_get_image_url_basic(self):
        """Test basic image URL generation."""
        adapter = ImageKitImages()
        adapter.settings.url_endpoint = "https://ik.imagekit.io/test"

        url = await adapter.get_image_url("test.jpg")

        assert url == "https://ik.imagekit.io/test/test.jpg"

    @pytest.mark.asyncio
    async def test_imagekit_get_image_url_with_transformations(self):
        """Test image URL with transformations."""
        adapter = ImageKitImages()
        adapter.settings.url_endpoint = "https://ik.imagekit.io/test"

        url = await adapter.get_image_url(
            "test.jpg", width=300, height=200, crop="maintain_ratio", quality=80
        )

        assert "test.jpg" in url
        assert "tr=w-300" in url
        assert "h-200" in url
        assert "c-maintain_ratio" in url
        assert "q-80" in url

    @pytest.mark.asyncio
    async def test_imagekit_upload_image(self):
        """Test image upload functionality."""
        adapter = ImageKitImages()
        adapter.settings.private_key = "test-private-key"
        adapter.settings.public_key = "test-public-key"
        adapter.settings.url_endpoint = "https://ik.imagekit.io/test"

        # Mock the ImageKit upload
        with patch("imagekitio.client.ImageKit.upload") as mock_upload:
            mock_upload.return_value = MagicMock(
                file_id="uploaded_file_id",
                url="https://ik.imagekit.io/test/uploaded_image.jpg",
            )

            result = await adapter.upload_image(b"fake_image_data", "test.jpg")

            assert result["file_id"] == "uploaded_file_id"
            assert "url" in result

    def test_imagekit_build_transformation_url(self):
        """Test transformation URL building."""
        adapter = ImageKitImages()
        adapter.settings.url_endpoint = "https://ik.imagekit.io/test"

        url = adapter._build_transformation_url(
            "test.jpg",
            {
                "width": 300,
                "height": 200,
                "crop": "maintain_ratio",
                "quality": 80,
                "format": "webp",
            },
        )

        assert "tr=w-300" in url
        assert "h-200" in url
        assert "c-maintain_ratio" in url
        assert "q-80" in url
        assert "f-webp" in url


@pytest.mark.unit
class TestImageAdapterIntegration:
    """Test image adapter integration patterns."""

    def test_multiple_adapters_coexistence(self):
        """Test multiple image adapters can coexist."""
        cloudinary = CloudinaryImages()
        imagekit = ImageKitImages()

        # Both should have different MODULE_IDs
        assert cloudinary.MODULE_ID != imagekit.MODULE_ID

        # Both should implement the same protocol
        assert hasattr(cloudinary, "get_img_tag")
        assert hasattr(imagekit, "get_img_tag")
        assert hasattr(cloudinary, "get_image_url")
        assert hasattr(imagekit, "get_image_url")

    @pytest.mark.asyncio
    async def test_adapter_error_handling(self):
        """Test adapter error handling."""
        adapter = CloudinaryImages()
        # No cloud_name set - should handle gracefully

        url = await adapter.get_image_url("test.jpg")
        # Should return fallback URL
        assert url == "test.jpg"

    def test_settings_validation(self):
        """Test settings validation."""
        # Test Cloudinary settings validation
        cloudinary_settings = CloudinaryImagesSettings()
        cloudinary_settings.cloud_name = "test-cloud"
        cloudinary_settings.api_key = "test-key"
        cloudinary_settings.api_secret = "test-secret"

        assert cloudinary_settings.cloud_name == "test-cloud"
        assert cloudinary_settings.api_key == "test-key"
        assert cloudinary_settings.api_secret == "test-secret"

        # Test ImageKit settings validation
        imagekit_settings = ImageKitImagesSettings()
        imagekit_settings.url_endpoint = "https://ik.imagekit.io/test"
        imagekit_settings.public_key = "test-public"
        imagekit_settings.private_key = "test-private"

        assert imagekit_settings.url_endpoint == "https://ik.imagekit.io/test"
        assert imagekit_settings.public_key == "test-public"
        assert imagekit_settings.private_key == "test-private"

    @pytest.mark.asyncio
    async def test_protocol_compliance(self):
        """Test all adapters comply with ImagesProtocol."""
        adapters = [CloudinaryImages(), ImageKitImages()]

        for adapter in adapters:
            # Test required methods exist and work
            img_tag = adapter.get_img_tag("test.jpg", "Test")
            assert isinstance(img_tag, str)
            assert "img" in img_tag

            image_url = await adapter.get_image_url("test.jpg")
            assert isinstance(image_url, str)
            assert len(image_url) > 0
