import pyotp
import qrcode
import io
import base64


def generate_totp_secret():

    return pyotp.random_base32()



def generate_qr_code(
    secret,
    email
):

    uri = pyotp.totp.TOTP(
        secret
    ).provisioning_uri(
        name=email,
        issuer_name="WalletFlow"
    )


    qr = qrcode.make(uri)


    buffer = io.BytesIO()

    qr.save(
        buffer,
        format="PNG"
    )


    image = base64.b64encode(
        buffer.getvalue()
    ).decode()


    return {
        "uri": uri,
        "qr_code":
        f"data:image/png;base64,{image}"
    }
