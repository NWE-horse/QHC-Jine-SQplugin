import asyncio
import logging

class Rcon:
    def __init__(self, options={}):
        for option in ["host", "port", "password"]:
            if option not in options:
                raise ValueError(f"{option} must be specified.")
        self.host = options["host"]
        self.port = options["port"]
        self.password = options["password"]
        self.client = None
        self.connected = False
        self.msgId = 1

    async def connect(self):
        if self.client and self.connected:
            raise Exception("Rcon already connected.")
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            logging.info(f"Connected to: {self.host}:{self.port}")
            await self.send_auth()
        except Exception as e:
            logging.error(f"Failed to connect: {e}")
            raise

    async def disconnect(self):
        if not self.connected or not self.writer:
            raise Exception("Rcon not connected.")
        logging.info(f"Disconnecting from: {self.host}:{self.port}")
        self.writer.close()
        await self.writer.wait_closed()
        self.connected = False

    async def execute(self, command):
        if not self.connected:
            raise Exception("Rcon not connected.")

        response = await self.send_command(command)
        return response

    async def send_command(self, command):
        if len(command.encode()) > 4154:
            logging.error("Command size too large.")
            return None

        self.writer.write(self.encode_command(2, self.msgId, command))
        await self.writer.drain()

        return await self.receive_response()

    async def receive_response(self):
        data = await self.reader.read(4096)
        return data

    def encode_command(self, command_type, id, body=""):
        size = len(body.encode()) + 14
        buffer = bytearray(size)
        buffer[0:4] = size.to_bytes(4, byteorder='little', signed=False)
        buffer[4:8] = id.to_bytes(4, byteorder='little', signed=False)
        buffer[8:12] = command_type.to_bytes(4, byteorder='little', signed=False)
        buffer[12:size - 2] = body.encode('utf-8')
        buffer[size - 2:size] = b'\x00\x00'
        return buffer

    async def send_auth(self):
        self.writer.write(self.encode_command(0x03, 2147483647, self.password))
        await self.writer.drain()
        # Assume we receive some kind of response indicating whether auth was successful
        response = await self.receive_response()
        logging.debug(f"Auth response: {response}")
        # Check if response is successful
        if b'Auth successful' not in response:  # Adjust this condition based on your actual expected response
            logging.error("Authentication failed.")
            raise Exception("Authentication failed.")


# Usage example
async def main():
    rcon = Rcon({"host": "180.188.21.82", "port": 25001, "password": "9UneFErmhxU6Knmreo9QSbgVQiRXyLrt"})
    await rcon.connect()
    response = await rcon.execute("ShowServerInfo")
    print(response)
    await rcon.disconnect()

asyncio.run(main())
