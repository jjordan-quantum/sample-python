# eth/BSC private key is 32 bytes long
# RSA key must be > private key
# RSA key must be 128 byte == 1024-bit because of required padding

import rsa
import time
import key


wallet_private_key = key.key
message = wallet_private_key.encode('utf8')

# Generate keys
time_0 = time.time()
print('Generating keys...')

(pubkey, privkey) = rsa.newkeys(1024)

time_1 = time.time()
print(f'Keys generated in {round(time_1-time_0, 3)} seconds')

# saving public key to file
saved_public_key = pubkey.save_pkcs1()
public_key_file = "public"
f = open(public_key_file, 'wb')
f.write(saved_public_key)
f.close()
print('Public key file generated')

# save private key to file
saved_private_key = privkey.save_pkcs1()
private_key_file = "private"
f = open(private_key_file, 'wb')
f.write(saved_private_key)
f.close()

# load public key from file
f = open(public_key_file, 'rb')
public_key_data = f.read()
f.close()
public_key = rsa.PublicKey.load_pkcs1(public_key_data)

# encrypt message with public key
crypto = rsa.encrypt(message, public_key)

# save encrypted message to file
crypto_file = "encrypted"
f = open(crypto_file, 'wb')
f.write(crypto)
f.close()
print('File written')

# read encrypted message from file
f = open(crypto_file, 'rb')
encrypted_message = f.read()
f.close()

# load private key from file
f = open(private_key_file, 'rb')
private_key_data = f.read()
f.close()
private_key = rsa.PrivateKey.load_pkcs1(private_key_data)

# decrypt message with private key
decrypted_message = rsa.decrypt(encrypted_message, private_key)
print(f"Decrypted: {decrypted_message.decode('utf8')}")

#print(f"Public key: {pubkey}")


