QUEUE_CAPACITY = 5


def enqueue(queue: list[str], item: str) -> list[str]:
    if len(queue) >= QUEUE_CAPACITY:
        raise OverflowError("queue is full")
    queue.append(item)
    return queue
