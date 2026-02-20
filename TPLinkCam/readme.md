
I need to stream tplink EC60 camera feed to computer. here is info i know and found online

EC60
IPv4 Address: 192.168.1.209

KC105
IPv4 Address
192.168.1.201


my tp link kasa account 
username: zhangyan612 or zhangyan612@gmail.com
password: zymeng90612



My Router

MAC address

34:60:f9:11:0e:26

Connection Info
Connection
Wi-Fi / 2.4 GHz
Connection Type
802.11n
Frequency
2.4
Protocol Supported
N
Encryption
WPA2
Radio Configuration
1 x 1 : 1
Phy Rate / Modulation Rate
72 Mbps
RSSI
-41
SNR
49
Network Info
Mac Address
34:60:f9:11:0e:26
Connected to
NCM1100
IPv4 Address
192.168.1.209
Subnet Mask
255.255.255.0
IPv4 DNS
192.168.1.1
IPv4 Address Allocation
Dynamic
Lease Type
DHCP
DHCP lease time remaining
1406 minutes 57 seconds
IPv6 LAN Prefix
2600:1008:a030:fa9a::/64
IPv6 Global
IPv6 Type / Address Allocation
Stateless
IPv6 link-local
::
IPv6 DNS
2600:1008:A030:FA9A:3A88:71FF:FE5F:C36E
Network Connection
Bridge
Ping Test
Test Connectivity
Time on the network
40 minutes 20 seconds










Who needs native RTSP support anyway? | How I setup a video feed with the tp-link Kasa EC60
I did not see any clear way of doing this online so posting this here so anyone looking to do the same can set something up or demo this themselves. This may work on other camera models in the tp-link lineup but this is the only one I've got so can't confirm/deny either way.

The tp-link Kasa EC60 cam is an affordable, decent quality indoor camera. One feature this model does not natively support is RTSP. I wanted a way to tap into the cameras video feed from a PC without having to use the mobile application. After a night of research, it seems that some other curious human's reverse engineering revealed some useful information.

This article discussed how authenticating to the camera's web services on TCP port 19443 can return an mjpeg stream of data. The author goes on to talk about how this stream could then be piped to ffmpeg to save the video feed.

I was more interested in getting that video feed into a media player for live viewing. This article talked about converting mjpeg to RTSP which I was finally able to accomplish with VLC. The redacted IP address represents the IP of the tp-link camera. All commands included below. I hope this unusual and niche piece of knowledge is able to help someone out there...

# First, open an mjpeg stream to the tp-link camera
# Pass the output to VLC and begin an RTSP stream on port 8554
curl -vv -k -u tp_link_user@email.com:$(echo -n "YOUR_TP_LINK_PASSWORD_HERE" | base64) "https://xxx.xxx.xxx.xxx:19443/https/stream/mixed?video=h264&audio=g711&resolution=hd" --ignore-content-length --output - | cvlc stream:///dev/stdin --sout '#rtp{access=udp,sdp=rtsp://:8554/stream}' :demux=h264
With that RTSP stream running, open VLC (or some other RTSP client, I suppose) and connect to the host performing the streaming at rtsp://X.X.X.X:8554/stream. Beware that the streaming command opens port 8554 globally and no password would be required to tap into the video feed. This is merely to demonstrate that it is theoretically possible to do this without native RTSP support in the camera.

It does seem that with doing this, the there is approximately 40 seconds of video latency, not sure if this is by design to prevent curious users like me from doing this or if it's just a product of some other technical restriction with the hardware. If anyone has any other suggestions, solutions or workarounds hit me up!


I know it's been a while on this, but I wanted to say thanks, and give an update. Using an EC60,

I followed the above instructions in a lubuntu vm on my Unraid server, but could also probably be run on something like a Pi or other linux systems. Once you have this RSTP 'daemon' running, you can further extend this by integrating it into MotionEye, which can be installed on raspberry pi's, or in my case I found a docker image for Motioneye in the Unraid store.

With the rstp program running, you can add the stream to Motioneye by adding a new camera, type 'Network Camera', put the url in (rtsp://xx.xx.xx.xx:8554/stream, IP of the server you ran the 'curl' command on), blank the user and password, and it should give you a choice of TCP or UDP cameras, choose UDP.

Viola! Now you can use Motioneye to set up motion detection/capture/notifications local. Motioneye will also integrate into Home Assistant for more IFTTT fun.

You can also try running multiple rtsp streams from one server by just changing the 8554 port to another number.

sdp=rtsp://:8554/stream

Not sure how many threads a server can run without bogging down, so YMMV.

