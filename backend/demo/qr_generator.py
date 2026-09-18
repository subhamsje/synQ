import io
import qrcode
import qrcode.image.svg


class QRGenerator:
    """
    Generates QR code representations linking directly to the FLTX Hackathon Demo Portal.
    """

    @staticmethod
    def generate_demo_qr_svg(target_url: str = "http://localhost:8000/demo") -> str:
        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
            image_factory=factory
        )
        qr.add_data(target_url)
        qr.make(fit=True)

        img = qr.make_image(attrib={'class': 'fltx-qr-code'})
        stream = io.BytesIO()
        img.save(stream)
        return stream.getvalue().decode('utf-8')


qr_generator = QRGenerator()
