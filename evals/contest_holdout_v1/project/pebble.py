QUEUE_CAPACITY = 5


def enqueue(queue: list[str], item: str) -> list[str]:
    queue.append(item)
    return queue
