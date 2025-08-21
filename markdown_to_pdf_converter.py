import base64
import io
import os
import tempfile
from pathlib import Path

import markdown
import pdfkit
import requests
from PIL import Image
from bs4 import BeautifulSoup


class MarkdownToPDFConverter:
	"""Core converter class (same as before but with progress callbacks)"""

	def __init__(self, wkhtmltopdf_path=None, progress_callback=None):
		self.wkhtmltopdf_path = wkhtmltopdf_path
		self.progress_callback = progress_callback
		self.temp_files = []

		self.config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path) if wkhtmltopdf_path else None

		self.pdf_options = {
			'page-size': 'A4',
			'margin-top': '0.75in',
			'margin-right': '0.75in',
			'margin-bottom': '0.75in',
			'margin-left': '0.75in',
			'encoding': "UTF-8",
			'no-outline': None,
			'enable-local-file-access': None
		}

	def read_markdown_file(self, file_path):
		try:
			with open(file_path, 'r', encoding='utf-8') as file:
				return file.read()
		except Exception as e:
			raise Exception(f"Error reading markdown file: {e}")

	def download_image(self, url, base_path=None):
		try:
			if not url.startswith(('http://', 'https://')):
				if base_path and not os.path.isabs(url):
					local_path = os.path.join(os.path.dirname(base_path), url)
				else:
					local_path = url

				if os.path.exists(local_path):
					with open(local_path, 'rb') as f:
						return f.read()
				else:
					return None

			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
			}
			response = requests.get(url, headers=headers, timeout=30)
			response.raise_for_status()
			return response.content

		except Exception:
			return None

	def optimize_image(self, image_data, max_width=800, quality=85):
		try:
			img = Image.open(io.BytesIO(image_data))

			if img.mode in ('RGBA', 'LA', 'P'):
				img = img.convert('RGB')

			if img.width > max_width:
				ratio = max_width / img.width
				new_height = int(img.height * ratio)
				img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

			output = io.BytesIO()
			img.save(output, format='JPEG', quality=quality, optimize=True)
			return output.getvalue()

		except Exception:
			return image_data

	def embed_images_in_html(self, html_content, base_path=None):
		soup = BeautifulSoup(html_content, 'html.parser')

		for img_tag in soup.find_all('img'):
			src = img_tag.get('src')
			if not src:
				continue

			image_data = self.download_image(src, base_path)
			if image_data:
				optimized_data = self.optimize_image(image_data)
				base64_data = base64.b64encode(optimized_data).decode('utf-8')
				img_tag['src'] = f"data:image/jpeg;base64,{base64_data}"

				style = img_tag.get('style', '')
				if 'max-width' not in style:
					style += 'max-width: 100%; height: auto;'
				img_tag['style'] = style

		return str(soup)

	def markdown_to_html(self, markdown_content):
		extensions = [
			'markdown.extensions.tables',
			'markdown.extensions.fenced_code',
			'markdown.extensions.codehilite',
			'markdown.extensions.toc',
		]

		md = markdown.Markdown(extensions=extensions)
		html_content = md.convert(markdown_content)
		return html_content

	def create_full_html(self, html_content, title="Converted Document"):
		css_styles = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                margin: 0;
                padding: 20px;
            }

            h1, h2, h3, h4, h5, h6 {
                color: #2c3e50;
                margin-top: 2em;
                margin-bottom: 1em;
            }

            h1 { font-size: 2.5em; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
            h2 { font-size: 2em; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }
            h3 { font-size: 1.5em; }

            p { margin-bottom: 1em; text-align: justify; }

            img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 20px auto;
                border-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }

            code {
                background-color: #f8f9fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }

            pre {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #3498db;
                overflow-x: auto;
                margin: 1em 0;
            }

            pre code {
                background: none;
                padding: 0;
            }

            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1em 0;
            }

            th, td {
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }

            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }

            blockquote {
                border-left: 4px solid #3498db;
                margin: 1em 0;
                padding-left: 20px;
                color: #666;
                font-style: italic;
            }

            ul, ol {
                margin: 1em 0;
                padding-left: 2em;
            }

            li {
                margin-bottom: 0.5em;
            }

            a {
                color: #3498db;
                text-decoration: none;
            }

            a:hover {
                text-decoration: underline;
            }
        </style>
        """

		full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            {css_styles}
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

		return full_html

	def convert_to_pdf(self, markdown_file_path, output_pdf_path=None, title=None):
		try:
			markdown_content = self.read_markdown_file(markdown_file_path)
			html_content = self.markdown_to_html(markdown_content)
			html_with_images = self.embed_images_in_html(html_content, markdown_file_path)

			if not title:
				title = Path(markdown_file_path).stem

			full_html = self.create_full_html(html_with_images, title)

			if not output_pdf_path:
				md_path = Path(markdown_file_path)
				output_pdf_path = md_path.parent / f"{md_path.stem}.pdf"

			with tempfile.NamedTemporaryFile(mode='w', suffix='.html',
			                                 delete=False, encoding='utf-8') as temp_html:
				temp_html.write(full_html)
				temp_html_path = temp_html.name
				self.temp_files.append(temp_html_path)

			pdfkit.from_file(temp_html_path, output_pdf_path,
			                 options=self.pdf_options, configuration=self.config)

			return output_pdf_path

		except Exception as e:
			raise Exception(f"Error converting to PDF: {e}")

		finally:
			self.cleanup()

	def cleanup(self):
		for temp_file in self.temp_files:
			try:
				if os.path.exists(temp_file):
					os.unlink(temp_file)
			except Exception:
				pass
		self.temp_files = []
