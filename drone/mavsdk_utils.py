async def get_mavlink_connection(mavsdk_cli):
    await mavsdk_cli.connect(system_address="udp://:14540")
    print("Waiting for drone...")
    async for state in mavsdk_cli.core.connection_state():
        if state.is_connected:
            print(f"Drone discovered: {state}")
            break

async def get_gps_data(mavsdk_cli):
    async for gps_data in mavsdk_cli.telemetry.raw_gps():
        return gps_data
