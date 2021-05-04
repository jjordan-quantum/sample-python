import rsa

def decrypt_key():
    # load/read encrypted wallet key from file
    crypto_file = "lib/encrypted"
    f = open(crypto_file, 'rb')
    encrypted_message = f.read()
    f.close()

    # load private key from file
    private_key_file = "lib/private"
    f = open(private_key_file, 'rb')
    private_key_data = f.read()
    f.close()
    private_key = rsa.PrivateKey.load_pkcs1(private_key_data)

    return rsa.decrypt(encrypted_message, private_key)