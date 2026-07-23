import cv2
import numpy as np
import object_socket

s = object_socket.ObjectReceiverSocket('127.0.0.1', 5000,
                                       print_when_connecting_to_sender=True,
                                       print_when_receiving_object=False)

left_top = (0, 0)
left_bottom = (0, 0)
right_top = (0, 0)
right_bottom = (0, 0)

while True:
    ret, frame = s.recv_object()

    if ret is False:
        break

    # Exercitiul 2: micsoram cadrul
    height, width, _ = frame.shape
    frame = cv2.resize(frame, (width // 2, height // 2))
    cv2.imshow('Small', frame)
    height, width, _ = frame.shape

    # Exercitiul 3: convertim cadrul la grayscale
    gray_frame = (frame.astype(np.uint32).sum(axis=2) // 3).astype(np.uint8)
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

    frame_bounds = np.array([screen_upper_right, screen_upper_left, screen_lower_left, screen_lower_right], dtype=np.float32)
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

    # Exercitiul 8: binarizam imaginea (threshold)
    sobel_uint8 = cv2.convertScaleAbs(combined)
    threshold = int(255 / 2)
    binarized = np.zeros_like(sobel_uint8)
    binarized[sobel_uint8 > threshold] = 255
    cv2.imshow('Binarized', binarized)

    # Exercitiul 9: coordonatele marcajelor (stanga/dreapta)
    cleaned = binarized.copy()
    margin = int(width * 0.05)
    cleaned[:, :margin] = 0
    cleaned[:, width - margin:] = 0
    cv2.imshow('Cleaned', cleaned)

    left_half = cleaned[:, :width // 2]
    right_half = cleaned[:, width // 2:]
    left_points = np.argwhere(left_half > 0)
    right_points = np.argwhere(right_half > 0)
    left_ys = left_points[:, 0]
    left_xs = left_points[:, 1]
    right_ys = right_points[:, 0]
    right_xs = right_points[:, 1] + width // 2

    # Exercitiul 10: gasim liniile prin regresie si le desenam
    smoothing = 0.85

    if len(left_xs) > 50:
        left_b, left_a = np.polynomial.polynomial.polyfit(left_xs, left_ys, deg=1)

        if abs(left_a) > 1.5:
            left_top_y = 0
            left_bottom_y = height
            left_top_x = (left_top_y - left_b) / left_a
            left_bottom_x = (left_bottom_y - left_b) / left_a

            if -10 ** 8 < left_top_x < 10 ** 8:
                new_x = int(left_top_x)
                left_top = (int(smoothing * left_top[0] + (1 - smoothing) * new_x), left_top_y)
            if -10 ** 8 < left_bottom_x < 10 ** 8:
                new_x = int(left_bottom_x)
                left_bottom = (int(smoothing * left_bottom[0] + (1 - smoothing) * new_x), left_bottom_y)

    if len(right_xs) > 50:
        right_b, right_a = np.polynomial.polynomial.polyfit(right_xs, right_ys, deg=1)

        if abs(right_a) > 1.5:
            right_top_y = 0
            right_bottom_y = height
            right_top_x = (right_top_y - right_b) / right_a
            right_bottom_x = (right_bottom_y - right_b) / right_a

            if -10 ** 8 < right_top_x < 10 ** 8:
                new_x = int(right_top_x)
                right_top = (int(smoothing * right_top[0] + (1 - smoothing) * new_x), right_top_y)
            if -10 ** 8 < right_bottom_x < 10 ** 8:
                new_x = int(right_bottom_x)
                right_bottom = (int(smoothing * right_bottom[0] + (1 - smoothing) * new_x), right_bottom_y)

    lines_frame = cleaned.copy()
    cv2.line(lines_frame, left_top, left_bottom, (200, 0, 0), 5)
    cv2.line(lines_frame, right_top, right_bottom, (100, 0, 0), 5)
    cv2.imshow('Lines', lines_frame)

    # Exercitiul 11: vizualizare finala (liniile suprapuse peste imaginea color)
    magic_matrix_inv = cv2.getPerspectiveTransform(frame_bounds, trapezoid_bounds_float)

    left_line_frame = np.zeros((height, width), dtype=np.uint8)
    cv2.line(left_line_frame, left_top, left_bottom, 255, 3)
    left_line_warped = cv2.warpPerspective(left_line_frame, magic_matrix_inv, (width, height))
    left_line_points = np.argwhere(left_line_warped > 0)

    right_line_frame = np.zeros((height, width), dtype=np.uint8)
    cv2.line(right_line_frame, right_top, right_bottom, 255, 3)
    right_line_warped = cv2.warpPerspective(right_line_frame, magic_matrix_inv, (width, height))
    right_line_points = np.argwhere(right_line_warped > 0)

    final_frame = frame.copy()
    if len(left_line_points) > 0:
        final_frame[left_line_points[:, 0], left_line_points[:, 1]] = (50, 50, 250)
    if len(right_line_points) > 0:
        final_frame[right_line_points[:, 0], right_line_points[:, 1]] = (50, 250, 50)

    # Exercitiul 12
    cv2.imshow('Final', final_frame)

    cv2.imshow('Original', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()