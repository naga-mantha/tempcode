def reverse_chunks(lst, chunk_size):
    '''
    Reverses a given list based on the chunk_size

    Example:
        data = [1, 2, 3, 4, 5, 6]
        result = reverse_chunks(data, 2)
        print(result)  # → [5, 6, 3, 4, 1, 2]
    '''
    return [
        element
        for i in range(len(lst), 0, -chunk_size)
        for element in lst[max(0, i-chunk_size):i]
    ]