"""Small shared helpers used by the recording, monitoring, and web scripts."""


def build_frame_vector(payload):
    """Combine flex + acc + gyro from one UDP payload into an 11-feature vector.

    Expected payload shape: {"flex": [5], "acc": [3], "gyro": [3]}

    Raises KeyError / TypeError if the payload is malformed so callers can
    skip bad packets instead of silently inserting zeros.
    """
    return (
        list(payload["flex"])
        + list(payload["acc"])
        + list(payload["gyro"])
    )
