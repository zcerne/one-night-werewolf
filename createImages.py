import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

class Image:
    def __init__(self, image_path) -> None:
        self.path = image_path

class Pdf:
    def __init__(self, images_folder_path: str, special_instructions_dict: dict, width_height: tuple, xy_spacing:tuple = (0.2, 0.2)):
        self.folder_path = images_folder_path
        self.special_instructions = special_instructions_dict
        self.img_w, self.img_h = width_height
        self.x_spacing, self.y_spacing = xy_spacing
        self.pdf_canvas = None

    def create_pdf(self, output_path: str = "output.pdf") -> None:
        # Create PDF canvas
        self.pdf_canvas = canvas.Canvas(output_path, pagesize=letter)
        page_width, page_height = letter

        # Collect all images to include (with repetitions)
        images_to_include = []
        for file in os.listdir(self.folder_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                if file in self.special_instructions:
                    n_of_copies = self.special_instructions[file]
                else:
                    n_of_copies = 1

                for _ in range(n_of_copies):
                    images_to_include.append(file)

        # Layout images side by side
        x_position = 0.5 * inch  # Left margin
        y_position = page_height - self.img_h - 0.5 * inch  # Top margin

        for image_file in images_to_include:
            image_path = os.path.join(self.folder_path, image_file)

            # Check if image fits on current line
            if x_position + self.img_w > page_width - 0.5 * inch:
                # Move to next line
                x_position = 0.5 * inch
                y_position -= self.img_h + self.y_spacing * inch  # Add custom vertical spacing

                # Check if we need a new page
                if y_position < 0.5 * inch:
                    self.pdf_canvas.showPage()
                    y_position = page_height - self.img_h - 0.5 * inch

            # Draw image
            self.pdf_canvas.drawImage(image_path, x_position, y_position,
                                    width=self.img_w, height=self.img_h)
            x_position += self.img_w + self.x_spacing * inch  # Move right with custom horizontal spacing

        # Save PDF
        self.pdf_canvas.save()

if __name__ == "__main__":
    special = {"villager.png":0, "werewolf.png": 0, "mason.png":0, "background.jpg":16, "seer.png":0, "troublemaker.png":0, "dopleganger.png":0, "drunk.png":0, "hunter.png":0, "insomniac.png":0, "rober.png":0, "tanner.png":0, "minion.png":0}
    # Create PDF with custom spacing (0.5 inch horizontal, 0.3 inch vertical)
    pdf = Pdf("Cards", special, (125, 190), xy_spacing=(0, 0))
    pdf.create_pdf()


