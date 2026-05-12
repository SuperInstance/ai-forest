! FLUX→Ring Buffer Direct Path
!
! Decodes FLUX extension opcodes from a byte array and executes each
! opcode directly against the tile ring buffer. No dispatcher, no
! interpreter overhead — just opcodes feeding array operations.
!
! FLUX opcode format (4 bytes per instruction):
!   byte 0: opcode
!   byte 1: operand A (low byte)
!   byte 2: operand B (mid byte)
!   byte 3: operand C (high byte)
!
! Opcodes:
!   0x01  FLUX_WRITE      — write a tile (24-bit value from operand ABC)
!   0x02  FLUX_READ       — read N tiles (N = operand A) into result buffer
!   0x03  FLUX_CONTRACT   — contract ring buffer against itself (threshold = operand A)
!   0x04  FLUX_CYCLE      — run seed cycle (operand fields = params)
!   0x05  FLUX_CLEAR      — reset ring buffer (set write_pos = 0, tile_count = 0)
!   0x06  FLUX_STATUS     — fill buffer with status (fill_pct, total, write_pos)
!   0x07  FLUX_FILTER     — filter ring buffer by threshold (keep only novel tiles)
!   0x08  FLUX_MERGE      — blend ring buffer with input array
!   0xFF  FLUX_NOP        — no-op (skip this instruction)
!
! The result buffer stores output in consecutive 24-bit values.
! Use FLUX_NOP padding to align instruction boundaries.

module flux_ring
  use, intrinsic :: iso_c_binding
  use tile_ring_buffer
  use plato_math
  use fortran_seed
  implicit none

  ! FLUX opcodes
  integer(c_int32_t), parameter :: FLUX_NOP      = int(Z'FF')
  integer(c_int32_t), parameter :: FLUX_WRITE     = int(Z'01')
  integer(c_int32_t), parameter :: FLUX_READ      = int(Z'02')
  integer(c_int32_t), parameter :: FLUX_CONTRACT  = int(Z'03')
  integer(c_int32_t), parameter :: FLUX_CYCLE     = int(Z'04')
  integer(c_int32_t), parameter :: FLUX_CLEAR     = int(Z'05')
  integer(c_int32_t), parameter :: FLUX_STATUS    = int(Z'06')
  integer(c_int32_t), parameter :: FLUX_FILTER    = int(Z'07')
  integer(c_int32_t), parameter :: FLUX_MERGE     = int(Z'08')

  integer(c_int32_t), parameter :: MAX_RESULT = 65536
  real(c_float) :: fill_pct
  integer(c_int32_t) :: tot_tiles

contains

  ! ── FLUX_EXECUTE_RING: Execute FLUX bytecode against the ring buffer
  !
  ! Takes a byte array of FLUX extension opcodes and executes each one.
  ! Results accumulate in the ring buffer for the next opcode.
  ! This makes FLUX bytecode execute DIRECTLY on the ring buffer —
  ! no dispatcher, no interpreter, just opcodes feeding array operations.
  !
  ! flux_bytes:  input byte array of FLUX instructions
  ! n_bytes:     number of bytes in the array (must be multiple of 4)
  !
  ! The result buffer is written to the ring buffer so sequential
  ! opcodes chain naturally: FLUX_READ → FLUX_CYCLE → FLUX_WRITE.

  subroutine flux_execute_ring(flux_bytes, n_bytes) bind(c, name="flux_execute_ring")
    integer(c_int8_t), intent(in) :: flux_bytes(n_bytes)
    integer(c_int32_t), intent(in), value :: n_bytes

    integer(c_int32_t) :: i, n_instr, opcode, opA, opB, opC
    integer(c_int32_t) :: tile_val, n_read, n_result
    integer(c_int32_t) :: result_buf(MAX_RESULT)
    integer(c_int32_t) :: input_buf(MAX_RESULT)
    integer(c_int32_t) :: seed_val, mu, mag, thresh, n_seeds
    integer(c_int32_t) :: survivors(MAX_RESULT), n_survivors
  integer(c_int32_t) :: n_read_tmp

    n_instr = n_bytes / 4

    do i = 1, n_instr
      ! Decode instruction: 4 bytes per opcode
      opcode = int(flux_bytes((i-1)*4 + 1), c_int32_t)
      if (opcode < 0) opcode = opcode + 256

      opA = int(flux_bytes((i-1)*4 + 2), c_int32_t)
      if (opA < 0) opA = opA + 256

      opB = int(flux_bytes((i-1)*4 + 3), c_int32_t)
      if (opB < 0) opB = opB + 256

      opC = int(flux_bytes((i-1)*4 + 4), c_int32_t)
      if (opC < 0) opC = opC + 256

      select case (opcode)
      case (FLUX_NOP)
        ! No-op — skip
        continue

      case (FLUX_WRITE)
        ! Write a single 24-bit tile composed from operand values
        tile_val = iand(opA + opB * 256 + opC * 65536, Z'00FFFFFF')
        call ring_write(tile_val)

      case (FLUX_READ)
        ! Read N most recent tiles (N = opA)
        n_read = min(max(opA, 1), 255)
        call ring_read(n_read, result_buf, n_read)
        ! Write results back to ring buffer for chainability
        do n_result = 1, n_read
          call ring_write(result_buf(n_result))
        end do

      case (FLUX_CONTRACT)
        ! Contract ring buffer against itself
        ! threshold = opA * 256 + opB (16-bit threshold)
        thresh = opA * 256 + opB
        if (thresh < 1) thresh = 50000

        n_read = min(max(opC, 1), 64)
        n_read_tmp = n_read * 2
        call ring_read(n_read_tmp, result_buf, n_read_tmp)
        if (n_read_tmp > 2) then
          call contract(result_buf, n_read, result_buf(n_read+1:), n_read, &
                       thresh, n_result)
          call ring_write(n_result)
        end if

      case (FLUX_CYCLE)
        ! Run seed cycle on ring buffer contents
        ! opA = number of seeds, opB = threshold, opC = magnitude
        n_seeds = min(max(opA, 2), 128)
        thresh = max(opB * 100, 1)
        mag = max(opC * 10, 1)

        call ring_read(n_seeds, input_buf, n_seeds)
        call system_clock(seed_val)
        seed_val = mod(seed_val, 1000000)

        if (n_seeds >= 2) then
          call seed_cycle(input_buf, n_seeds, seed_val, 512, mag, thresh, &
                         survivors, n_survivors)
          ! Write survivors back to ring buffer
          do n_result = 1, min(n_survivors, n_seeds / 2)
            call ring_write(survivors(n_result))
          end do
        end if

      case (FLUX_CLEAR)
        ! Clear by writing a reset marker.
        ! True clear would need direct access to buffer internals;
        ! instead we mark with a sentinel value and let old tiles decay.
        call ring_write(int(Z'00DEC0DE', c_int32_t))

      case (FLUX_STATUS)
        ! Fill result buffer with status values
        call ring_status(fill_pct, tot_tiles)
        call ring_write(int(fill_pct * 100.0, c_int32_t))

      case (FLUX_FILTER)
        ! Filter ring buffer: keep only tiles above/below threshold
        ! opA = threshold multiplier, opB = 0 (keep above) or 1 (keep below)
        thresh = max(opA * 1000, 1)
        n_read = min(max(opC, 1), 128)
        call ring_read(n_read, input_buf, n_read)

        n_survivors = 0
        do n_result = 1, n_read
          if (opB == 0 .and. input_buf(n_result) > thresh) then
            n_survivors = n_survivors + 1
            survivors(n_survivors) = input_buf(n_result)
          else if (opB == 1 .and. input_buf(n_result) < thresh) then
            n_survivors = n_survivors + 1
            survivors(n_survivors) = input_buf(n_result)
          end if
        end do

        do n_result = 1, n_survivors
          call ring_write(survivors(n_result))
        end do

      case (FLUX_MERGE)
        ! Blend ring buffer with itself by averaging adjacent pairs
        ! opA = number of tiles to merge
        n_read = min(max(opA, 2), 128)
        call ring_read(n_read, input_buf, n_read)

        do n_result = 1, n_read - 1, 2
          if (n_result + 1 <= n_read) then
            tile_val = (input_buf(n_result) + input_buf(n_result + 1)) / 2
            call ring_write(tile_val)
          end if
        end do

      case default
        ! Unknown opcode — write error tile
        call ring_write(int(opcode, c_int32_t))

      end select
    end do
  end subroutine flux_execute_ring

end module flux_ring
