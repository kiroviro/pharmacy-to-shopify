"""
Leaflet Parser

Extracts content from pharmaceutical product leaflets.

Prescription products have standardized leaflet sections:
- "Какво представлява X и за какво се използва" -> Details
- "Какво съдържа X" -> Composition
- "Как да използвате X" -> Usage
- "Възможни нежелани реакции" -> More Info

This parser also handles clinical pharmacology text from JSON-LD data,
splitting it into logical sections.
"""

from bs4 import BeautifulSoup


class LeafletParser:
    """
    Parses pharmaceutical leaflet sections.

    Usage:
        parser = LeafletParser(soup)
        details = parser.extract_section("Детайли")
        composition = parser.extract_section("Състав")
    """

    # Section markers for different tabs
    SECTION_MARKERS = {
        "Детайли": {
            "start": ["Какво представлява", "представлява"],
            "end": ["Какво трябва да знаете", "Какво съдържа"]
        },
        "Състав": {
            "start": ["Какво съдържа", "съдържа"],
            "end": ["Как да използвате", "Как да приемате"]
        },
        "Начин на употреба": {
            "start": ["Как да използвате", "Как да приемате", "Препоръчителна доза"],
            "end": ["Възможни нежелани", "нежелани реакции", "Как да съхранявате"]
        },
        "Повече информация": {
            "start": ["Възможни нежелани", "нежелани реакции"],
            "end": ["Срок на годност", "Притежател"]
        }
    }

    def __init__(self, soup: BeautifulSoup):
        """
        Initialize the leaflet parser.

        Args:
            soup: BeautifulSoup object of the page
        """
        self.soup = soup
        self._page_text = None

    @property
    def page_text(self) -> str:
        """Lazy-load page text."""
        if self._page_text is None:
            self._page_text = self.soup.get_text()
        return self._page_text

    def extract_section(self, tab_name: str, max_length: int = 3000) -> str:
        """
        Extract specific section from pharmaceutical leaflet.

        Args:
            tab_name: Name of the section to extract
            max_length: Maximum length of extracted text

        Returns:
            HTML-formatted section content or empty string
        """
        markers = self.SECTION_MARKERS.get(tab_name)
        if not markers:
            return ""

        # Find start position
        start_pos = -1
        for start_marker in markers["start"]:
            pos = self.page_text.find(start_marker)
            if pos != -1:
                start_pos = pos
                break

        if start_pos == -1:
            return ""

        # Find end position
        end_pos = len(self.page_text)
        for end_marker in markers["end"]:
            # Start search after start marker to avoid finding the marker itself
            pos = self.page_text.find(end_marker, start_pos + 50)
            if pos != -1 and pos < end_pos:
                end_pos = pos

        # Extract section text
        section_text = self.page_text[start_pos:end_pos].strip()

        # Limit length
        if len(section_text) > max_length:
            section_text = section_text[:max_length] + "..."

        return self.text_to_html(section_text) if section_text else ""

    def parse_clinical_pharmacology(self, text: str, section_name: str) -> str:
        """
        Parse specific sections from JSON-LD clinicalPharmacology field.

        The clinicalPharmacology field contains multiple sections with
        line breaks. This method extracts the relevant section.

        Args:
            text: Full clinicalPharmacology text
            section_name: Name of section to extract

        Returns:
            HTML-formatted section content or empty string
        """
        if not text:
            return ""

        if section_name == "Детайли":
            # Extract main description (first part before "Приложение")
            if "Приложение:" in text:
                parts = text.split("Приложение:")
                return self.text_to_html(parts[0])
            # Return first 500 chars if no clear section marker
            return self.text_to_html(text[:500])

        elif section_name == "Начин на употреба":
            # Extract usage instructions (after "Приложение:")
            if "Приложение:" in text:
                parts = text.split("Приложение:")
                if len(parts) > 1:
                    # Get content up to next major section
                    usage = parts[1]
                    usage = usage.split("Активнo веществo:")[0]
                    usage = usage.split("Предпазни мерки:")[0]
                    return self.text_to_html(usage)

        elif section_name == "Повече информация":
            # Extract warnings and additional info
            if "Предпазни мерки:" in text:
                parts = text.split("Предпазни мерки:")
                if len(parts) > 1:
                    warnings = parts[1].split("Вид на опаковката:")[0]
                    return self.text_to_html(warnings)

            # Or packaging info at the end
            if "Вид на опаковката:" in text:
                parts = text.split("Вид на опаковката:")
                if len(parts) > 1:
                    return self.text_to_html(parts[1])

        return ""

    def text_to_html(self, text: str) -> str:
        """
        Convert plain text with line breaks to HTML with paragraphs and lists.

        Args:
            text: Plain text with line breaks

        Returns:
            HTML-formatted string
        """
        if not text:
            return ""

        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        paragraphs = text.split('\n\n')

        html_parts = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            lines = [line.strip() for line in para.split('\n') if line.strip()]

            # Detect if it's a bulleted list (lines ending with semicolon)
            is_list = False
            if len(lines) > 2:
                semicolon_endings = sum(1 for line in lines if line.endswith(';'))
                if semicolon_endings >= len(lines) * 0.6:  # 60% threshold
                    is_list = True

            if is_list:
                # Convert to HTML list
                html_parts.append('<ul>')
                for line in lines:
                    # Skip header-like lines
                    if line and not line.endswith(':'):
                        # Remove trailing semicolon
                        line = line.rstrip(';').strip()
                        if line:
                            html_parts.append(f'<li>{line}</li>')
                html_parts.append('</ul>')
            else:
                # Check for section headers (short lines ending with colon)
                if para.endswith(':') and len(para) < 80 and '\n' not in para:
                    html_parts.append(f'<h4>{para}</h4>')
                else:
                    # Regular paragraph - preserve internal line breaks
                    if '\n' in para and len(lines) > 1:
                        formatted = '<br>'.join(lines)
                        html_parts.append(f'<p>{formatted}</p>')
                    else:
                        html_parts.append(f'<p>{para}</p>')

        return '\n'.join(html_parts)

    def has_leaflet_content(self) -> bool:
        """
        Check if the page contains pharmaceutical leaflet content.

        Returns:
            True if page has leaflet-style content
        """
        leaflet_indicators = [
            "Какво представлява",
            "Какво съдържа",
            "Как да използвате",
            "Възможни нежелани реакции",
            "листовка",
        ]

        for indicator in leaflet_indicators:
            if indicator in self.page_text:
                return True

        return False
