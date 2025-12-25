#!/usr/bin/env python3
import time

import libevdev

# ===== Configurations =====
INVERT_SCROLL = True  # Invert scroll direction (True = natural scrolling)
CLICK_TIME = 0.25  # Maximum time for a single click (seconds)
RIGHT_CLICK_TAP = 0.2  # Maximum time for two-finger right-click tap (seconds)
MOVE_THRESHOLD = 1  # Minimum movement to trigger cursor move (pixels)
SCROLL_THRESHOLD = 8  # Minimum vertical movement to trigger scroll (pixels)
MOVE_SCALE = 0.35  # Cursor movement scaling factor (lower = slower)
DOUBLE_CLICK_TIMEOUT = (
    0.4  # Maximum time between clicks for double-click drag (seconds)
)

# ===== ANSI color =====
C_GRN = "\033[32m"
C_RED = "\033[31m"
C_YLW = "\033[33m"
C_BLU = "\033[34m"
C_RST = "\033[0m"

# ===== Touchscreen device =====
device_path = "/dev/input/event26"  # It's for Moonlight game stream, idk if this script works in other devices


def main():
    try:
        fd = open(device_path, "rb")
    except PermissionError:
        print(f"{C_RED}[ERROR]{C_RST} Cannot open {device_path}: permission denied")
        print(
            f"{C_RED}[ERROR]{C_RST} You may need to run this script with sudo or add your user to the 'input' group"
        )
        return
    dev = libevdev.Device(fd)
    dev.grab()

    vdev = libevdev.Device()
    vdev.name = "Adaptive Virtual Touchpad"
    for code in [
        libevdev.EV_REL.REL_X,
        libevdev.EV_REL.REL_Y,
        libevdev.EV_REL.REL_WHEEL,
    ]:
        vdev.enable(code)
    for code in [libevdev.EV_KEY.BTN_LEFT, libevdev.EV_KEY.BTN_RIGHT]:
        vdev.enable(code)

    uinput = vdev.create_uinput_device()
    print(f"{C_GRN}--- Adaptive Touchpad ---{C_RST}")

    slots = {}
    last_pos = {}
    slot2id = {}

    cur_slot = 0
    main_finger_id = None
    touch_start_time = 0.0
    moved_far = False
    in_touch_cycle = False
    dragging = False
    last_click_time = 0.0
    click_count = 0

    try:
        for ev in dev.events():
            if ev.matches(libevdev.EV_ABS.ABS_MT_SLOT):
                cur_slot = ev.value

            elif ev.matches(libevdev.EV_ABS.ABS_MT_TRACKING_ID):
                if ev.value != -1:
                    tid = ev.value
                    old_id = slot2id.get(cur_slot)
                    if old_id is not None and old_id != tid:
                        slots.pop(old_id, None)
                        last_pos.pop(old_id, None)
                    slot2id[cur_slot] = tid
                    slots[tid] = {
                        "slot": cur_slot,
                        "x": None,
                        "y": None,
                        "press_time": time.time(),
                    }

                    if not in_touch_cycle:
                        main_finger_id = tid
                        touch_start_time = time.time()
                        moved_far = False
                        in_touch_cycle = True
                        # Check for double-click drag mode
                        current_time = time.time()
                        if (
                            current_time - last_click_time < DOUBLE_CLICK_TIMEOUT
                            and click_count == 1
                        ):
                            # Start dragging immediately on double-click
                            dragging = True
                            uinput.send_events(
                                [
                                    libevdev.InputEvent(libevdev.EV_KEY.BTN_LEFT, 1),
                                    libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
                                ]
                            )
                            print(
                                f"{C_BLU}[DOUBLE CLICK DRAG]{C_RST} Double-click detected, dragging started"
                            )
                        else:
                            pass
                        print(
                            f"{C_GRN}[DOWN]{C_RST} Slot {cur_slot} Tracking {tid} Pressing(Main finger)"
                        )
                    else:
                        print(
                            f"{C_YLW}[SECOND DOWN]{C_RST} Slot {cur_slot} Tracking {tid} Pressing(Second finger, may as right click)"
                        )
                        # Cancel dragging if second finger touches
                        if dragging:
                            uinput.send_events(
                                [
                                    libevdev.InputEvent(libevdev.EV_KEY.BTN_LEFT, 0),
                                    libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
                                ]
                            )
                            dragging = False
                            print(
                                f"{C_RED}[DRAG]{C_RST} Cancel dragging due to second finger"
                            )

                else:
                    tid = slot2id.get(cur_slot)
                    if tid is not None:
                        press_time = slots.get(tid, {}).get("press_time", time.time())
                        duration = time.time() - press_time
                        print(
                            f"{C_RED}[UP]{C_RST} Slot {cur_slot} Tracking {tid} Release(Duration: {duration:.2f}s)"
                        )

                        if tid != main_finger_id and duration < RIGHT_CLICK_TAP:
                            uinput.send_events(
                                [
                                    libevdev.InputEvent(libevdev.EV_KEY.BTN_RIGHT, 1),
                                    libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
                                    libevdev.InputEvent(libevdev.EV_KEY.BTN_RIGHT, 0),
                                    libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
                                ]
                            )
                            print(f"{C_BLU}[CLICK]{C_RST} Right Click")

                        slots.pop(tid, None)
                        last_pos.pop(tid, None)
                        slot2id.pop(cur_slot, None)

                        if tid == main_finger_id and in_touch_cycle:
                            total_time = time.time() - touch_start_time
                            if (
                                not dragging
                                and not moved_far
                                and total_time < CLICK_TIME
                            ):
                                uinput.send_events(
                                    [
                                        libevdev.InputEvent(
                                            libevdev.EV_KEY.BTN_LEFT, 1
                                        ),
                                        libevdev.InputEvent(
                                            libevdev.EV_SYN.SYN_REPORT, 0
                                        ),
                                        libevdev.InputEvent(
                                            libevdev.EV_KEY.BTN_LEFT, 0
                                        ),
                                        libevdev.InputEvent(
                                            libevdev.EV_SYN.SYN_REPORT, 0
                                        ),
                                    ]
                                )
                                print(f"{C_BLU}[CLICK]{C_RST} Left Click")
                                # Record click time for double-click detection
                                current_time = time.time()
                                if (
                                    current_time - last_click_time
                                    < DOUBLE_CLICK_TIMEOUT
                                ):
                                    click_count += 1
                                else:
                                    click_count = 1
                                last_click_time = current_time
                                print(f"{C_YLW}[CLICK COUNT]{C_RST} {click_count}")
                            # End dragging if dragging
                            if dragging:
                                uinput.send_events(
                                    [
                                        libevdev.InputEvent(
                                            libevdev.EV_KEY.BTN_LEFT, 0
                                        ),
                                        libevdev.InputEvent(
                                            libevdev.EV_SYN.SYN_REPORT, 0
                                        ),
                                    ]
                                )
                                dragging = False
                                print(f"{C_RED}[DRAG]{C_RST} Stop dragging")
                            # Reset double-click drag mode when finger releases
                            in_touch_cycle = False
                            main_finger_id = None

            elif ev.matches(libevdev.EV_ABS.ABS_MT_POSITION_X):
                tid = slot2id.get(cur_slot)
                if tid in slots:
                    slots[tid]["x"] = ev.value
            elif ev.matches(libevdev.EV_ABS.ABS_MT_POSITION_Y):
                tid = slot2id.get(cur_slot)
                if tid in slots:
                    slots[tid]["y"] = ev.value

            if ev.matches(libevdev.EV_SYN.SYN_REPORT):
                active = [
                    tid
                    for tid, s in slots.items()
                    if s["x"] is not None and s["y"] is not None
                ]

                dx = dy = count = 0
                for tid in active:
                    if tid in last_pos:
                        dx += slots[tid]["x"] - last_pos[tid][0]
                        dy += slots[tid]["y"] - last_pos[tid][1]
                        count += 1
                    last_pos[tid] = (slots[tid]["x"], slots[tid]["y"])

                if count:
                    avg_dx = dx / count
                    avg_dy = dy / count

                    if abs(avg_dx) > MOVE_THRESHOLD or abs(avg_dy) > MOVE_THRESHOLD:
                        moved_far = True
                        out = []

                        if len(active) >= 2:
                            if abs(avg_dy) > SCROLL_THRESHOLD:
                                wheel_val = 1 if avg_dy < 0 else -1
                                if INVERT_SCROLL:
                                    wheel_val *= -1
                                out.append(
                                    libevdev.InputEvent(
                                        libevdev.EV_REL.REL_WHEEL, wheel_val
                                    )
                                )
                        else:
                            # Single finger movement
                            if not dragging:
                                # Only double-click mode can start dragging
                                # No delayed drag (traditional touchpad behavior)
                                pass
                            # Always send movement events
                            out.extend(
                                [
                                    libevdev.InputEvent(
                                        libevdev.EV_REL.REL_X, int(avg_dx * MOVE_SCALE)
                                    ),
                                    libevdev.InputEvent(
                                        libevdev.EV_REL.REL_Y, int(avg_dy * MOVE_SCALE)
                                    ),
                                ]
                            )

                        if out:
                            uinput.send_events(
                                out
                                + [libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)]
                            )

    except KeyboardInterrupt:
        pass
    finally:
        dev.ungrab()


if __name__ == "__main__":
    main()
