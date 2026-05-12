! Fortran Compute Claw — Matrix Operations for PLATO Room Tensors
!
! Loaded as a shared library by the Python mycelium bridge.
! Each call is a tiny Fortran instance: contract, return, vanish.
!
! The 24-bit tile format for Fortran:
!   INTEGER(c_int32_t) :: raw   ! 24-bit tile, stored in low 24 bits
!   Pack 64M tiles into a 192MB array — one BLAS call on the whole batch.

module plato_math
  use, intrinsic :: iso_c_binding
  implicit none

  ! Tile batch — packed 24-bit integers
  integer(c_int32_t), parameter :: MAX_TILES = 65536
  integer(c_int32_t), parameter :: TILE_MASK = int(Z'00FFFFFF', c_int32_t)
  integer(c_int32_t), parameter :: SCHEME_MASK = int(Z'00C00000', c_int32_t)

  contains

  ! ── Contract two rooms: Σ(room_a × room_b) for each paired tile
  !
  ! Called from Python via ctypes:
  !   contract_tiles(room_a, na, room_b, nb, result, threshold)
  !
  ! Returns: for each tile in room_a, compute dot-product with each tile in room_b
  !          if result > threshold, keep it (they're related)
  !          result is same tile value with confidence boosted by overlap
  !
  ! This is the core PLATO tensor contraction. Called every time rooms connect.

  subroutine contract_tiles(room_a, na, room_b, nb, result, nresult, threshold) &
       bind(c, name="contract_tiles")
    integer(c_int32_t), intent(in)  :: room_a(na)
    integer(c_int32_t), intent(in)  :: room_b(nb)
    integer(c_int32_t), intent(in), value :: na, nb
    integer(c_int32_t), intent(out) :: result(na * nb)
    integer(c_int32_t), intent(out) :: nresult
    real(c_float), intent(in), value :: threshold

    integer(c_int32_t) :: i, j, a_val, b_val, ca, ga, cb, gb, cr, gr, idx
    real(c_float) :: sim

    nresult = 0
    idx = 0

    do i = 1, na
       a_val = iand(room_a(i), TILE_MASK)
       ca = iand(shiftr(a_val, 18), 63)
       ga = iand(shiftr(a_val, 12), 63)

       do j = 1, nb
          idx = idx + 1
          b_val = iand(room_b(j), TILE_MASK)
          cb = iand(shiftr(b_val, 18), 63)
          gb = iand(shiftr(b_val, 12), 63)

          sim = (real(ca, c_float) * real(cb, c_float) + real(ga, c_float) * real(gb, c_float)) / 8192.0

          if (sim > threshold) then
             nresult = nresult + 1
             cr = min(int(ca * sim + cb * (1.0 - sim), c_int32_t), 63)
             gr = min(int(ga + gb / 2, c_int32_t), 63)
             result(nresult) = ior(ior(shiftl(cr, 18), shiftl(gr, 12)), iand(a_val, 4095))
             result(nresult) = iand(result(nresult), TILE_MASK)
          end if
       end do
    end do
  end subroutine contract_tiles


  ! ── Spline interpolation between two room states
  !
  ! Given two room snapshots (before, after) at time t, compute the interpolated
  ! state at t+δ. Each tile moves along the spline:
  !   tile(t+δ) = (1-μ) × tile_before + μ × tile_after
  ! where μ = δ / (max_time - t)

  subroutine spline_interp(before, after, n, mu, result) &
       bind(c, name="spline_interp")
    integer(c_int32_t), intent(in)  :: before(*), after(*)
    integer(c_int32_t), intent(in), value :: n
    real(c_float), intent(in), value :: mu
    integer(c_int32_t), intent(out) :: result(*)

    integer(c_int32_t) :: i
    real(c_float) :: conf_f, grad_f

    do i = 1, n
       conf_f = real(iand(shiftr(before(i), 18), 63), c_float) * (1.0 - mu) + &
                real(iand(shiftr(after(i), 18), 63), c_float) * mu
       grad_f = real(iand(shiftr(before(i), 12), 63), c_float) * (1.0 - mu) + &
                real(iand(shiftr(after(i), 12), 63), c_float) * mu
       result(i) = ior(iand(before(i), 4095), &
            ior(shiftl(min(int(conf_f, c_int32_t), 63), 18), &
                shiftl(min(int(grad_f, c_int32_t), 63), 12)))
       ! ε + ctx preserved from before
       result(i) = ior(result(i), iand(before(i), 4095))
    end do
  end subroutine spline_interp


  ! ── Batch gradient: compute Δ between consecutive tiles
  !
  ! Returns the gradient array: the amount each tile changed from
  ! the previous cycle. Used by the forest floor for drift detection.

  subroutine batch_gradient(tiles, n, gradients) &
       bind(c, name="batch_gradient")
    integer(c_int32_t), intent(in)  :: tiles(*)
    integer(c_int32_t), intent(in), value :: n
    integer(c_int32_t), intent(out) :: gradients(*)

    integer(c_int32_t) :: i

    !$omp parallel do
    do i = 2, n
       gradients(i) = iand(abs(tiles(i) - tiles(i-1)), TILE_MASK)
    end do
    !$omp end parallel do
    gradients(1) = 0  ! first tile has no predecessor
  end subroutine batch_gradient


  ! ── Physics report: tell the bridge how fast we are
  !
  ! The library self-reports its performance characteristics.
  ! This is the "assembly port declares its physics" principle.

  subroutine get_physics(latency_ns, flops, simd_width) &
       bind(c, name="get_physics")
    real(c_float), intent(out) :: latency_ns
    real(c_float), intent(out) :: flops
    integer(c_int32_t), intent(out) :: simd_width

    ! These are compile-time constants for this build.
    ! On ARM64 NEON: 120-element registers
    ! On x86 AVX-512: 512-bit = 16 single-precision floats at once
    latency_ns = 12.0    ! 12ns average instruction latency
    flops = 1.2e10       ! 12 GFLOPS (ARM64 NEON estimate)
    simd_width = 16      ! 128-bit NEON registers on ARM64
  end subroutine get_physics


  ! ── FILTER: return tiles where confidence >= min_conf AND gradient >= min_grad
  !
  ! Used by: ftile grep — find tiles matching field criteria in batch

  subroutine tile_filter(tiles_in, n_in, min_conf, min_grad, tiles_out, n_out) &
       bind(c, name="tile_filter")
    integer(c_int32_t), intent(in)  :: tiles_in(*)
    integer(c_int32_t), intent(in), value :: n_in, min_conf, min_grad
    integer(c_int32_t), intent(out) :: tiles_out(*)
    integer(c_int32_t), intent(out) :: n_out

    integer(c_int32_t) :: i, conf, grad, val
    n_out = 0

    do i = 1, n_in
       val = iand(tiles_in(i), TILE_MASK)
       conf = iand(shiftr(val, 18), 63)
       grad = iand(shiftr(val, 12), 63)
       if (conf >= min_conf .and. grad >= min_grad) then
          n_out = n_out + 1
          tiles_out(n_out) = tiles_in(i)
       end if
    end do
  end subroutine tile_filter


  ! ── MERGE: combine two tile arrays, keep higher confidence on conflict
  !
  ! Used by: ftile merge — merge two room snapshots

  subroutine tile_merge(tiles_a, na, tiles_b, nb, result, n_result) &
       bind(c, name="tile_merge")
    integer(c_int32_t), intent(in)  :: tiles_a(*), tiles_b(*)
    integer(c_int32_t), intent(in), value :: na, nb
    integer(c_int32_t), intent(out) :: result(*)
    integer(c_int32_t), intent(out) :: n_result

    integer(c_int32_t) :: i, j, conf_a, conf_b, val_a, val_b, found
    n_result = 0

    ! Copy all from A
    do i = 1, na
       n_result = n_result + 1
       result(n_result) = tiles_a(i)
    end do

    ! Add from B if not already present, or upgrade confidence
    do i = 1, nb
       val_b = iand(tiles_b(i), TILE_MASK)
       conf_b = iand(shiftr(val_b, 18), 63)
       found = 0

       do j = 1, n_result
          val_a = iand(result(j), TILE_MASK)
          ! Match on lower 12 bits (eps + ctx = identity)
          if (iand(val_a, 4095) == iand(val_b, 4095)) then
             found = j
             exit
          end if
       end do

       if (found > 0) then
          ! Upgrade confidence if B has higher
          conf_a = iand(shiftr(iand(result(found), TILE_MASK), 18), 63)
          if (conf_b > conf_a) then
             result(found) = ior(iand(result(found), 4095), &
                  ior(shiftl(int(conf_b, c_int32_t), 18), &
                      iand(val_b, 261888)))  ! keep grad from B too
          end if
       else
          n_result = n_result + 1
          result(n_result) = tiles_b(i)
       end if
    end do
  end subroutine tile_merge


  ! ── CANON: extract top N tiles by confidence
  !
  ! Used by: ftile canon — find best tiles in a room

  subroutine tile_canon(tiles_in, n_in, n_top, tiles_out, n_out) &
       bind(c, name="tile_canon")
    integer(c_int32_t), intent(in)  :: tiles_in(*)
    integer(c_int32_t), intent(in), value :: n_in, n_top
    integer(c_int32_t), intent(out) :: tiles_out(*)
    integer(c_int32_t), intent(out) :: n_out

    integer(c_int32_t) :: i, j, conf_i, conf_j, val_i, val_j, temp
    integer(c_int32_t) :: indices(65536)  ! max tiles for sorting
    n_out = min(n_in, n_top)

    ! Simple selection sort by confidence (n is small for canon ops)
    do i = 1, n_in
       indices(i) = i
    end do

    do i = 1, n_out
       do j = i + 1, n_in
          conf_i = iand(shiftr(iand(tiles_in(indices(i)), TILE_MASK), 18), 63)
          conf_j = iand(shiftr(iand(tiles_in(indices(j)), TILE_MASK), 18), 63)
          if (conf_j > conf_i) then
             temp = indices(i)
             indices(i) = indices(j)
             indices(j) = temp
          end if
       end do
       tiles_out(i) = tiles_in(indices(i))
    end do
  end subroutine tile_canon
end module plato_math
