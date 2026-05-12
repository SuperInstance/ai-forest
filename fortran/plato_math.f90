! PLATO Compute Claw — Native 32-bit Array Operations
!
! Fortran knows integers and arrays. This code does what Fortran is optimized for:
!   • Contiguous int32 arrays
!   • Simple loops the compiler can auto-vectorize
!   • OpenMP for parallel sections
!   • Stride-1 memory access (column-major = contiguous)
!
! No bit masking. No field extraction. No packing.
! The values ARE the data. Fortran just does the math.
!
! Written for gfortran -O3 -fopenmp -march=native

module plato_math
  use, intrinsic :: iso_c_binding
  implicit none
contains

  ! ── CONTRACT: count how many pairs are above threshold
  !
  ! Pure array operation. Takes two int32 arrays of length na and nb.
  ! Returns the NUMBER of pairs where |a(i) - b(j)| > threshold.
  ! Fortran auto-vectorizes the inner loop.
  !
  ! The threshold is in units of int32 — not normalized.
  ! A threshold of 100 means "pairs that differ by more than 100."

  subroutine contract(a, na, b, nb, threshold, nresult) &
       bind(c, name="contract")
    integer(c_int32_t), intent(in)  :: a(na), b(nb)
    integer(c_int32_t), intent(in), value :: na, nb, threshold
    integer(c_int32_t), intent(out) :: nresult

    integer(c_int32_t) :: i, j

    nresult = 0

    !$omp parallel do reduction(+:nresult) private(j)
    do i = 1, na
       do j = 1, nb
          if (abs(a(i) - b(j)) > threshold) then
             nresult = nresult + 1
          end if
       end do
    end do
    !$omp end parallel do
  end subroutine contract


  ! ── DOT: weighted dot product between two arrays
  !
  ! For each paired element, compute a(i) * b(i), accumulate.
  ! Used for: similarity scoring when caller provides aligned arrays.

  subroutine dot(a, b, n, result) &
       bind(c, name="dot")
    integer(c_int32_t), intent(in)  :: a(n), b(n)
    integer(c_int32_t), intent(in), value :: n
    integer(c_int64_t), intent(out) :: result

    integer(c_int32_t) :: i

    result = 0
    !$omp parallel do reduction(+:result)
    do i = 1, n
       result = result + int(a(i), c_int64_t) * int(b(i), c_int64_t)
    end do
    !$omp end parallel do
  end subroutine dot


  ! ── SPLINE: linear interpolation between two arrays
  !
  ! result(i) = before(i) + mu * (after(i) - before(i))
  ! mu is an integer 0-1023 representing 0.0 to 1.0

  subroutine spline(before, after, n, mu, result) &
       bind(c, name="spline")
    integer(c_int32_t), intent(in)  :: before(n), after(n)
    integer(c_int32_t), intent(in), value :: n, mu
    integer(c_int32_t), intent(out) :: result(n)

    integer(c_int32_t) :: i
    integer(c_int64_t) :: diff

    do i = 1, n
       diff = int(after(i) - before(i), c_int64_t) * int(mu, c_int64_t) / 1024
       result(i) = before(i) + int(diff, c_int32_t)
    end do
  end subroutine spline


  ! ── GRADIENT: absolute differences between consecutive elements
  !
  ! result(1) = 0
  ! result(i) = abs(a(i) - a(i-1)) for i > 1

  subroutine gradient(a, n, result) &
       bind(c, name="gradient")
    integer(c_int32_t), intent(in)  :: a(n)
    integer(c_int32_t), intent(in), value :: n
    integer(c_int32_t), intent(out) :: result(n)

    integer(c_int32_t) :: i

    result(1) = 0
    !$omp parallel do
    do i = 2, n
       result(i) = abs(a(i) - a(i-1))
    end do
    !$omp end parallel do
  end subroutine gradient


  ! ── FILTER: return indices where abs(value - target) < tolerance
  !
  ! Used for: finding values within a range

  subroutine filter_val(a, n, target, tolerance, indices, n_found) &
       bind(c, name="filter_val")
    integer(c_int32_t), intent(in)  :: a(n)
    integer(c_int32_t), intent(in), value :: n, target, tolerance
    integer(c_int32_t), intent(out) :: indices(n)
    integer(c_int32_t), intent(out) :: n_found

    integer(c_int32_t) :: i

    n_found = 0
    do i = 1, n
       if (abs(a(i) - target) <= tolerance) then
          n_found = n_found + 1
          indices(n_found) = i
       end if
    end do
  end subroutine filter_val


  ! ── PHYSICS: self-report compiler-visible performance characteristics
  !
  ! These are compile-time constants. The bridge reads them once at startup.

  subroutine physics(latency_ns, flops, simd_bits) &
       bind(c, name="physics")
    real(c_float), intent(out) :: latency_ns, flops
    integer(c_int32_t), intent(out) :: simd_bits

    latency_ns = 12.0
    flops = 1.2e10
    simd_bits = 128
  end subroutine physics

end module plato_math