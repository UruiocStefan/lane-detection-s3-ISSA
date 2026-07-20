import cv2
import numpy as np

cam = cv2.VideoCapture('Lane Detection Test Video 01.mp4')

while True:
    ret, frame = cam.read()

    if ret is False:
        break

    # Exercitiul 2: micsoram cadrul
    height, width, _ = frame.shape
    frame = cv2.resize(frame, (width // 2, height // 2))
    cv2.imshow('Small', frame)
    height, width, _ = frame.shape

    # Exercitiul 3: convertim cadrul la grayscale
    gray_frame = np.zeros((height, width), dtype=np.uint8)
    for row in range(height):
        for col in range(width):
            b, g, r = frame[row, col]
            gray_frame[row, col] = (int(b) + int(g) + int(r)) // 3
    cv2.imshow('Grayscale', gray_frame)

    # Exercitiul 4: selectam doar drumul (trapezoid)
    upper_left = (int(width * 0.45), int(height * 0.75))
    upper_right = (int(width * 0.55), int(height * 0.75))
    lower_left = (0, height)
    lower_right = (width, height)
    trapezoid_bounds = np.array([upper_right, upper_left, lower_left, lower_right], dtype=np.int32)
    trapezoid_frame = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(trapezoid_frame, trapezoid_bounds, 1)
    cv2.imshow('Trapezoid', trapezoid_frame * 255)
    road = gray_frame * trapezoid_frame
    cv2.imshow('Road', road)

    # Exercitiul 5: vedere de sus
    screen_upper_left = (0, 0)
    screen_upper_right = (width, 0)
    screen_lower_left = (0, height)
    screen_lower_right = (width, height)

    frame_bounds = np.array([screen_upper_right, screen_upper_left, screen_lower_left, screen_lower_right],dtype=np.float32)
    trapezoid_bounds_float = np.float32(trapezoid_bounds)
    magic_matrix = cv2.getPerspectiveTransform(trapezoid_bounds_float, frame_bounds)
    top_down = cv2.warpPerspective(road, magic_matrix, (width, height))
    cv2.imshow('Top-Down', top_down)

    # Exercitiul 6: adaugam putin blur
    blurred = cv2.blur(top_down, ksize=(5, 5))
    cv2.imshow('Blur', blurred)

    # Exercitiul 7: detectare muchii cu filtrul Sobel
    sobel_vertical = np.float32([[-1, -2, -1],
                                 [0, 0, 0],
                                 [1, 2, 1]])

    sobel_horizontal = np.transpose(sobel_vertical)
    blurred_float = np.float32(blurred)
    sobel_v_result = cv2.filter2D(blurred_float, -1, sobel_vertical)
    sobel_h_result = cv2.filter2D(blurred_float, -1, sobel_horizontal)

    cv2.imshow('Sobel Vertical', cv2.convertScaleAbs(sobel_v_result))
    cv2.imshow('Sobel Horizontal', cv2.convertScaleAbs(sobel_h_result))
    combined = np.sqrt(sobel_v_result ** 2 + sobel_h_result ** 2)
    cv2.imshow('Sobel', cv2.convertScaleAbs(combined))

    cv2.imshow('Original', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()