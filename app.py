import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import cv2
from PIL import Image
import time

import process

previous_time = time.perf_counter() # [sec]

st.image("data/logo.png", width=400)

st.title("KuchiYomi: mouth shape recognition")
st.write("Kyutech, [Saitoh-lab](https://www.saitoh-lab.com/)")
st.markdown("---")

#import platform
#import psutil

#st.write("OS: " + platform.platform())
#st.write("CPU: %.0f MHz" % psutil.cpu_freq().current)
#st.write("RAM: total %.1f GB, used %.1f %%" % (psutil.virtual_memory().total / 1024.0 / 1024.0 / 1024.0, psutil.virtual_memory().percent))
#st.write("GPU: ", torch.cuda.is_available())

target_person_id = st.selectbox("select target model (person)", ("P05", "P00", "P01", "P02", "P03", "P04", "P05", "P08", "P09", "P11", "P12",
                                                        "P14", "P15", "P21", "P22", "P24", "P25", "P26", "P27", "P28", "P29",
                                                        "P30", "P31", "P32", "P33", "P34", "P35", "P36", "P37", "P38", "P39",
                                                        "P40", "P41", "P42"))

process.set_model(target_person_id)

RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)


class VideoProcessor:
    def __init__(self) -> None:
        self.is_mirroring = True
        self.current_time = time.perf_counter()

    def recv(self, frame):
        image_cv = frame.to_ndarray(format="bgr24")

        image_height, image_width, channels = image_cv.shape[:3]
        
        out_image_cv = process.lip_reading(image_cv, self.is_mirroring)

        cv2.ellipse(out_image_cv, ((image_width//2, image_height//2), (image_height//3, image_height//2), 0), (255, 255, 255))

        str = "%d x %d pixel, %.1f fps" % (image_width, image_height, 1.0 / (time.perf_counter() - self.current_time))
        cv2.putText(out_image_cv, str, (20, image_height-20), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1)
        self.current_time = time.perf_counter()

        return av.VideoFrame.from_ndarray(out_image_cv, format="bgr24")


webrtc_ctx = webrtc_streamer(
    key="example",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": True, "audio": False},
    video_processor_factory=VideoProcessor,
    async_processing=True,
)


if webrtc_ctx.video_processor:
    webrtc_ctx.video_processor.is_mirroring = st.checkbox("Check the checkbox to flip horizontally.", value=True)
    #webrtc_ctx.video_processor.target_person_id = st.selectbox("select target person", ("P00", "P01", "P14", "P21", "P25", "P26"))
