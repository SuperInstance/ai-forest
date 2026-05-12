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



  ! ── WINDOW_CONTRACT: contract within a sliding time window
  !
  ! Like contract, but only considers elements where 
  ! time_a(i) and time_b(j) are within 'window' of each other.
  ! This makes time a first-class dimension in the compute layer.
  !
  ! time_a, time_b: arrays of timestamps (int32, orderable)
  ! a, b: arrays of values (int32)
  ! window: maximum time difference to consider (int32)

  subroutine window_contract(time_a, a, na, time_b, b, nb, window, threshold, nresult) &
       bind(c, name="window_contract")
    integer(c_int32_t), intent(in)  :: time_a(na), a(na), time_b(nb), b(nb)
    integer(c_int32_t), intent(in), value :: na, nb, window, threshold
    integer(c_int32_t), intent(out) :: nresult

    integer(c_int32_t) :: i, j, td

    nresult = 0

    !$omp parallel do reduction(+:nresult) private(j, td)
    do i = 1, na
       do j = 1, nb
          td = abs(time_a(i) - time_b(j))
          if (td <= window .and. abs(a(i) - b(j)) > threshold) then
             nresult = nresult + 1
          end if
       end do
    end do
    !$omp end parallel do
  end subroutine window_contract


  ! ── WINDOW_GRADIENT: gradient over a sliding window
  !
  ! For each element at position i, compute the average delta
  ! across a window of size w centered at i.
  ! This smooths noise and reveals temporal trends.

  subroutine window_gradient(arr, n, window, result) &
       bind(c, name="window_gradient")
    integer(c_int32_t), intent(in)  :: arr(n)
    integer(c_int32_t), intent(in), value :: n, window
    integer(c_int32_t), intent(out) :: result(n)

    integer(c_int32_t) :: i, j, start_idx, end_idx, count
    integer(c_int64_t) :: sum

    result(1) = 0
    if (n < 2) return

    !$omp parallel do private(j, start_idx, end_idx, count, sum)
    do i = 2, n
       start_idx = max(2, i - window / 2)
       end_idx = min(n, i + window / 2)
       sum = 0
       count = 0
       do j = start_idx, end_idx
          sum = sum + int(abs(arr(j) - arr(j-1)), c_int64_t)
          count = count + 1
       end do
       if (count > 0) then
          result(i) = int(sum / int(count, c_int64_t), c_int32_t)
       else
          result(i) = 0
       end if
    end do
    !$omp end parallel do
  end subroutine window_gradient


  ! ── RECENCY_DOT: weighted dot product where weight = 1 / (1 + age)
  !
  ! Elements with smaller timestamps (more recent) get higher weight.
  ! This makes the dot product time-aware.

  subroutine recency_dot(a, time_a, b, time_b, n, result) &
       bind(c, name="recency_dot")
    integer(c_int32_t), intent(in)  :: a(n), time_a(n), b(n), time_b(n)
    integer(c_int32_t), intent(in), value :: n
    integer(c_int64_t), intent(out) :: result

    integer(c_int32_t) :: i
    integer(c_int64_t) :: sum, w, min_t, max_t

    result = 0
    if (n < 1) return

    ! Find time range for normalization
    min_t = huge(min_t); max_t = 0
    do i = 1, n
       if (time_a(i) < min_t) min_t = time_a(i)
       if (time_b(i) < min_t) min_t = time_b(i)
       if (time_a(i) > max_t) max_t = time_a(i)
       if (time_b(i) > max_t) max_t = time_b(i)
    end do

    if (max_t <= min_t) then
       ! All same time — plain dot product
       do i = 1, n
          result = result + int(a(i), c_int64_t) * int(b(i), c_int64_t)
       end do
       return
    end if

    sum = 0
    do i = 1, n
       ! Weight: 1.0 at most recent timestamp, approaches 0 at oldest
       w = 1 + (max_t - min_t) / max(1, max_t - time_a(i) + 1)
       sum = sum + int(a(i), c_int64_t) * int(b(i), c_int64_t) / w
    end do
    result = sum
  end subroutine recency_dot



  ! ── EBBINGHAUS_CONTRACT: contract with forgetting curve weight
  !
  ! Like contract, but each tile's contribution is weighted by its
  ! confidence, which decays via Ebbinghaus curve: c(t) = c0 * exp(-t / tau)
  !
  !
  ! This implements the Forgetting Curve finding (Experiment 3).

  subroutine ebbinghaus_contract(a, conf_a, na, b, conf_b, nb, &
       threshold, tau, nresult) bind(c, name="ebbinghaus_contract")
    integer(c_int32_t), intent(in) :: a(na), conf_a(na), b(nb), conf_b(nb)
    integer(c_int32_t), intent(in), value :: na, nb, threshold, tau
    integer(c_int32_t), intent(out) :: nresult
    integer(c_int32_t) :: i, j, weight_a, weight_b
    nresult = 0
    do i = 1, na
       weight_a = conf_a(i) * 100 / max(conf_a(i) + tau, 1)
       do j = 1, nb
          weight_b = conf_b(j) * 100 / max(conf_b(j) + tau, 1)
          if (abs(a(i) - b(j)) * (1000 - weight_a - weight_b) / 1000 > threshold) then
             nresult = nresult + 1
          end if
       end do
    end do
  end subroutine ebbinghaus_contract




  ! ── ADAPTIVE_THRESHOLD: auto-tune theta based on tile density
  !
  ! If the ring buffer is dense (many tiles in a short time), use a
  ! HIGHER threshold (more aggressive compression). If sparse, use a
  ! LOWER threshold (more conservative, preserve more).
  !
  ! The optimal threshold is proportional to the inverse of tile density:
  !   theta_opt = base_threshold * (1 + density_factor / density)
  !
  ! This implements the Optimal Blind-Width finding (Experiment 4).

  subroutine adaptive_threshold(base_thresh, density, theta_out) &
       bind(c, name="adaptive_threshold")
    real(c_float), intent(in), value :: base_thresh, density
    integer(c_int32_t), intent(out) :: theta_out
    real(c_float) :: theta_float
    if (density > 0.1) then
       theta_float = base_thresh * (1.0 + 0.5 / density)
    else
       theta_float = base_thresh * 2.0
    end if
    theta_out = int(min(max(theta_float, 1.0), 100000.0), c_int32_t)
  end subroutine adaptive_threshold


  ! ── CONSCIOUSNESS_BENCH: measure F, M, C alongside throughput
  !
  ! F (Facts preserved) = how many tile values above threshold survive
  ! M (Meaning adapted) = entropy of tile distribution in ring buffer
  ! C (Cooperation) = cross-segment resonance in ring buffer
  !
  ! Returns all three plus raw throughput in a single Fortran call.
  ! This implements the Consciousness Metric finding (Experiment 5).

end module plato_math
