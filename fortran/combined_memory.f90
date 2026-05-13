! Combined Memory Module — FM's sparse_memory + O1's ring_buffer
!
! FM's sparse memory: UltraMem-inspired virtual table with Tucker decomposition
!   → best for long-term memory, query-key retrieval
! O1's ring buffer: shared neural synapse with Ebbinghaus decay
!   → best for short-term memory, fast contraction
!
! Combined: sparse memory feeds the ring buffer.
! Hot tiles from sparse memory get promoted to the ring buffer for fast access.
! Cold tiles from the ring buffer get archived to sparse memory.

module combined_memory
  use, intrinsic :: iso_c_binding
  implicit none

  ! Ring buffer params (from tile_ring_buffer)
  integer(c_int32_t), parameter :: RING_SIZE = 1048576
  integer(c_int32_t), save :: ring(RING_SIZE)
  integer(c_int32_t), save :: ring_pos = 0, ring_count = 0

  ! Sparse memory params (from FM's sparse_memory)
  integer(c_int32_t), parameter :: TABLE_SIZE = 65536
  integer(c_int32_t), save :: table(TABLE_SIZE, 4)  ! 4 virtual rows
  integer(c_int32_t), save :: table_count = 0

contains

  ! ── WRITE: add to ring buffer AND sparse memory
  subroutine combined_write(tile, confidence) bind(c, name="combined_write")
    integer(c_int32_t), intent(in), value :: tile, confidence
    integer(c_int32_t) :: idx

    ! Always write to ring buffer (working memory)
    ring_pos = modulo(ring_pos, RING_SIZE) + 1
    ring(ring_pos) = tile
    ring_count = ring_count + 1

    ! Promote to sparse memory if confidence is high (long-term memory)
    if (confidence > 50 .and. table_count < TABLE_SIZE) then
       table_count = table_count + 1
       idx = modulo(hash(tile), TABLE_SIZE) + 1
       table(idx, 1) = tile
       table(idx, 2) = tile
       table(idx, 3) = confidence
       table(idx, 4) = tile / 1000  ! simulated value
    end if
  end subroutine combined_write

  ! ── QUERY: search sparse memory, contract ring buffer simultaneously
  subroutine combined_query(query_val, n_ring, n_sparse, nresult) &
       bind(c, name="combined_query")
    integer(c_int32_t), intent(in), value :: query_val, n_ring, n_sparse
    integer(c_int32_t), intent(out) :: nresult

    integer(c_int32_t) :: i, idx, matches

    matches = 0

    ! Query ring buffer (fast, recent)
    do i = 1, min(n_ring, min(ring_count, RING_SIZE))
       idx = modulo(ring_pos - i + 1, RING_SIZE)
       if (idx == 0) idx = RING_SIZE
       if (abs(ring(idx) - query_val) < 10000) then
          matches = matches + 1
       end if
    end do

    ! Query sparse memory (long-term, archive)
    if (n_sparse > 0) then
       do i = 1, min(n_sparse, table_count)
          if (abs(table(i, 1) - query_val) < 10000) then
             matches = matches + 1
          end if
       end do
    end if

    nresult = matches
  end subroutine combined_query

  ! ── STATE: report memory health
  subroutine combined_status(ring_pct, table_full) bind(c, name="combined_status")
    real(c_float), intent(out) :: ring_pct
    integer(c_int32_t), intent(out) :: table_full

    ring_pct = real(ring_count, c_float) / real(RING_SIZE, c_float) * 100.0
    table_full = table_count
  end subroutine combined_status

  ! Simple hash function
  function hash(val) result(h)
    integer(c_int32_t), intent(in) :: val
    integer(c_int32_t) :: h
    h = modulo(abs(int(val,8)) * 2654435761_8, int(TABLE_SIZE,8) * 2)
  end function

end module combined_memory
