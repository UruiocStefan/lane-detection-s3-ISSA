import cv2
import object_socket


s = object_socket.ObjectSenderSocket('127.0.0.1', 5000,
                                     print_when_awaiting_receiver=True,
                                     print_when_sending_object=False)

cam = cv2.VideoCapture('Lane Detection Test Video 01.mp4')

while True:
    ret, frame = cam.read()

    s.send_object((ret, frame))

    if ret is False:
        break

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
