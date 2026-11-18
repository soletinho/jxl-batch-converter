"""
Unit and integration tests for JXL Batch Converter.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image

from src.downloader import ensure_cjxl, is_cjxl_available
from src.scanner import scan_images
from src.engine import JXLEngine, ConversionConfig
from src.reporter import ConversionReport, format_bytes


class TestJXLConverter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cjxl_path = ensure_cjxl()
        cls.engine = JXLEngine(cls.cjxl_path)

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="jxl_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_sample_jpeg(self, filename="sample.jpg", size=(120, 120), color=(100, 150, 200)) -> Path:
        p = self.test_dir / filename
        img = Image.new("RGB", size, color=color)
        img.save(p, "JPEG", quality=90)
        return p

    def _create_sample_png(self, filename="sample.png", size=(120, 120), color=(200, 100, 50, 255)) -> Path:
        p = self.test_dir / filename
        img = Image.new("RGBA", size, color=color)
        img.save(p, "PNG")
        return p

    def test_binary_available(self):
        self.assertTrue(is_cjxl_available())
        self.assertTrue(self.cjxl_path.exists())

    def test_scanner_discovers_images(self):
        self._create_sample_jpeg("img1.jpg")
        self._create_sample_png("img2.png")
        sub = self.test_dir / "subdir"
        sub.mkdir()
        img3 = sub / "img3.jpeg"
        Image.new("RGB", (50, 50)).save(img3, "JPEG")

        # Non-image file to ensure it gets ignored
        (self.test_dir / "notes.txt").write_text("hello")

        # Recursive scan
        images = scan_images(self.test_dir, recursive=True)
        self.assertEqual(len(images), 3)

        # Non-recursive scan
        images_non_rec = scan_images(self.test_dir, recursive=False)
        self.assertEqual(len(images_non_rec), 2)

    def test_lossless_conversion_jpeg(self):
        jpg = self._create_sample_jpeg("test.jpg")
        config = ConversionConfig(quality_mode="lossless")

        result = self.engine.convert_file(jpg, self.test_dir, config)
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.output_path)
        self.assertTrue(result.output_path.exists())
        self.assertGreater(result.original_size, 0)
        self.assertGreater(result.converted_size, 0)
        self.assertGreater(result.saved_bytes, 0)

    def test_custom_quality_conversion_png(self):
        png = self._create_sample_png("test.png")
        config = ConversionConfig(quality_mode="custom", quality=85)

        result = self.engine.convert_file(png, self.test_dir, config)
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.output_path)
        self.assertTrue(result.output_path.exists())

    def test_webp_conversion(self):
        webp_path = self.test_dir / "sample.webp"
        img = Image.new("RGBA", (150, 150), color=(50, 180, 120, 255))
        img.save(webp_path, "WEBP", quality=85)

        config = ConversionConfig(quality_mode="lossless")
        result = self.engine.convert_file(webp_path, self.test_dir, config)
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.output_path)
        self.assertTrue(result.output_path.exists())
        self.assertGreater(result.converted_size, 0)

    def test_report_generation(self):
        jpg1 = self._create_sample_jpeg("a.jpg")
        jpg2 = self._create_sample_jpeg("b.jpg")
        config = ConversionConfig(quality_mode="lossless")

        results = self.engine.batch_convert([jpg1, jpg2], self.test_dir, config)
        report = ConversionReport(results, self.test_dir)

        m = report.metrics
        self.assertEqual(m["total_files"], 2)
        self.assertEqual(m["success_count"], 2)
        self.assertGreater(m["total_saved_bytes"], 0)

        # Text summary
        text_summary = report.generate_text_summary()
        self.assertIn("RELATÓRIO DE CONVERSÃO JPEG XL", text_summary)

        # Export CSV
        csv_file = self.test_dir / "report.csv"
        report.export_csv(csv_file)
        self.assertTrue(csv_file.exists())
        self.assertGreater(csv_file.stat().st_size, 0)

        # Export HTML
        html_file = self.test_dir / "report.html"
        report.export_html(html_file)
        self.assertTrue(html_file.exists())
        self.assertGreater(html_file.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
