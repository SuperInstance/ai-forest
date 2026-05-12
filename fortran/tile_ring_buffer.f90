! Tile Ring Buffer — Shared memory synapse between all PLATO layers.
!
! Each 24-bit tile is a neuron firing. The ring buffer is the synapse
! between the Fortran compute layer, the Zig bridge, the Python runtime,
! the git daemon, and every agent.
!
! All layers read from and write to the same buffer. No copies. No passing.
! The buffer IS the shared state. The tile IS the signal.
!
! Architecture:
!
!   Git Daemon ──┐
!   Python RT   ──┼──► Ring Buffer (shared memory) ──► Fortran .so
!   Agent Cycle ──┘          │                            │
!                            │ 24-bit tiles               │ 21B/s
!                            ▼                            ▼
!                       PLATO rooms                  Contract results
!
! The buffer is a circular array of 24-bit integers.
! Writers append. Readers consume by index.
! The same buffer feeds every layer.

module tile_ring_buffer
  use, intrinsic :: iso_c_binding
  implicit none

  ! Buffer size: 1M tiles = 4MB (fits in L3 cache on ARM64)
  integer(c_int32_t), parameter :: BUFFER_SIZE = 1048576
  integer(c_int32_t), parameter :: TILE_MASK = int(Z'00FFFFFF', c_int32_t)

  ! Shared state
  integer(c_int32_t), save :: buffer(BUFFER_SIZE)
  integer(c_int32_t), save :: write_pos = 0
  integer(c_int32_t), save :: read_pos = 0
  integer(c_int32_t), save :: tile_count = 0

contains

  ! ── WRITE: append a 24-bit tile to the ring buffer
  !
  ! Called by any layer that produces a tile.
  ! The Fortran compute claw. The git daemon. The agent runtime.
  ! All write to the same buffer. No locking needed for single-writer.

  subroutine ring_write(tile) bind(c, name="ring_write")
    integer(c_int32_t), intent(in), value :: tile

    write_pos = modulo(write_pos, BUFFER_SIZE) + 1
    buffer(write_pos) = iand(tile, TILE_MASK)
    tile_count = tile_count + 1
  end subroutine ring_write


  ! ── READ: read the N most recent tiles from the ring buffer
  !
  ! Called by the Fortran compute claw to get fresh tiles for contraction.
  ! Called by the Zig dispatcher to batch opcodes for execution.
  ! Called by the Python runtime to feed the agent cycle.

  subroutine ring_read(n, result, n_read) bind(c, name="ring_read")
    integer(c_int32_t), intent(in), value :: n
    integer(c_int32_t), intent(out) :: result(*)
    integer(c_int32_t), intent(out) :: n_read

    integer(c_int32_t) :: i, pos

    n_read = min(n, min(tile_count, BUFFER_SIZE))
    do i = 1, n_read
       pos = modulo(write_pos - n_read + i, BUFFER_SIZE)
       if (pos == 0) pos = BUFFER_SIZE
       result(i) = buffer(pos)
    end do
  end subroutine ring_read


  ! ── CONTRACT_RING: contract the ring buffer against itself
  !
  ! The ring buffer IS the room. No PLATO read needed.
  ! Contract recent tiles against older tiles directly in Fortran.
  ! This is the neural synapse: recent firing patterns vs memory patterns.

  subroutine contract_ring(n_recent, n_memory, threshold, nresult) &
       bind(c, name="contract_ring")
    integer(c_int32_t), intent(in), value :: n_recent, n_memory, threshold
    integer(c_int32_t), intent(out) :: nresult

    integer(c_int32_t) :: i, j, ri, mi, val_r, val_m

    nresult = 0
    if (tile_count < n_recent + n_memory) return

    do i = 1, n_recent
       ri = modulo(write_pos - i, BUFFER_SIZE)
       if (ri == 0) ri = BUFFER_SIZE
       val_r = buffer(ri)

       do j = 1, n_memory
          mi = modulo(write_pos - n_recent - j, BUFFER_SIZE)
          if (mi == 0) mi = BUFFER_SIZE
          val_m = buffer(mi)

          if (abs(val_r - val_m) > threshold) then
             nresult = nresult + 1
          end if
       end do
    end do
  end subroutine contract_ring


  ! ── STATUS: report buffer state (how full, how many tiles)
  !
  ! Used by the daemon to monitor buffer health.

  subroutine ring_status(fill_pct, total) bind(c, name="ring_status")
    real(c_float), intent(out) :: fill_pct
    integer(c_int32_t), intent(out) :: total

    fill_pct = real(tile_count, c_float) / real(BUFFER_SIZE, c_float) * 100.0
    total = tile_count
  end subroutine ring_status

end module tile_ring_buffer
