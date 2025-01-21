from aiohttp import web
import aiohttp_cors
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration

# Global variables
video_track = None
peer_connections = set()

# Ice server configuration
ice_servers = [
    RTCIceServer(urls="stun:stun.l.google.com:19302")  # Google's public STUN server
]
configuration = RTCConfiguration(iceServers=ice_servers)

# Create a new peer connection
def create_peer_connection():
    global configuration
    pc = RTCPeerConnection(configuration)

    @pc.on("track")
    async def on_track(track):
        global video_track
        print(f"Track added: {track.kind}")
        if track.kind == "video":
            video_track = track

    @pc.on("icecandidate")
    async def on_icecandidate(candidate):
        if candidate:
            print(f"New ICE Candidate: {candidate}")
        else:
            print("All ICE candidates have been gathered.")

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print("ICE connection state is %s" % pc.iceConnectionState)
        if pc.iceConnectionState == "failed":
            print("ICE connection failed.")

    peer_connections.add(pc)
    return pc

# Consume endpoint
async def consume(request):
    global video_track
    if not video_track:
        return web.json_response({"error": "no broadcast"}, status=400)

    data = await request.json()
    sdp = data["sdp"]["sdp"]

    # Create a peer connection
    pc = create_peer_connection()

    # Set remote description
    await pc.setRemoteDescription(RTCSessionDescription(sdp, "offer"))

    # Add the video track
    if video_track:
        pc.addTrack(video_track)
        print("Video track added.")

    # Create and set local answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({
        "type": pc.localDescription.type,
        "sdp": pc.localDescription.sdp
    })

# Broadcast endpoint
async def broadcast(request):
    data = await request.json()
    sdp = data["sdp"]["sdp"]

    # Create a peer connection
    pc = create_peer_connection()

    # Set remote description
    await pc.setRemoteDescription(RTCSessionDescription(sdp, "offer"))

    # Create and set local answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({
        "type": pc.localDescription.type,
        "sdp": pc.localDescription.sdp
    })

# Serve index.html for testing
async def index(request):
    return web.Response(text="desperation")

# Initialize and start the server
app = web.Application()

# Add routes
app.router.add_get("/", index)
app.router.add_post("/webrtc/consume", consume)
app.router.add_post("/webrtc/broadcast", broadcast)

# Configure CORS
cors = aiohttp_cors.setup(app, defaults={
    "http://127.0.0.1:4100": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    ),
    "https://nighthawkcoders.github.io": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
    ),
    # Add other specific origins if needed, for example:
    # "http://another-allowed-origin.com": aiohttp_cors.ResourceOptions(
    #     allow_credentials=True,
    #     expose_headers="*",
    #     allow_headers="*",
    # )
})

# Apply CORS to each route explicitly
for route in list(app.router.routes()):
    cors.add(route)

# Run the app
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Aiohttp WebRTC Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=443, help="Port for HTTP server (default: 8080)")
    args = parser.parse_args()

    web.run_app(app, host=args.host, port=args.port)
