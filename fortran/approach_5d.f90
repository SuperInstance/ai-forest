! 5D Approach Space — FM's twistor-inspired knowledge evaluation
!
! Every tile is a point in 5D approach space, evaluated across:
!   1. COHERENCE — how well the tile fits with its neighbors
!   2. NOVELTY   — how different the tile is from past tiles
!   3. CONNECTIVITY — how many other tiles reference this one
!   4. AGE       — how old the tile is (Ebbinghaus decay)
!   5. VALUE     — the tile's contribution to consciousness metric FxC
!
! Like Penrose twistors, the tile encodes ALL five dimensions simultaneously.

module approach_5d
  use, intrinsic :: iso_c_binding
  implicit none

  real(c_float), parameter :: DIM_WEIGHTS(5) = [0.25, 0.20, 0.20, 0.15, 0.20]

contains

  subroutine approach_5d_eval(tiles_in, n, ages, &
       coherence_out, novelty_out, connectivity_out, age_out, value_out) &
       bind(c, name="approach_5d_eval")
    integer(c_int32_t), intent(in)  :: tiles_in(n), ages(n)
    integer(c_int32_t), intent(in), value :: n
    real(c_float), intent(out) :: coherence_out(n), novelty_out(n)
    real(c_float), intent(out) :: connectivity_out(n), age_out(n), value_out(n)

    integer(c_int32_t) :: i, j, diff_sum, max_age
    real(c_float) :: nov_raw

    if (n < 1) return
    max_age = maxval(ages)
    if (max_age <= 0) max_age = 1

    do i = 1, n
       ! Coherence: fit with adjacent tiles
       if (i > 1 .and. i < n) then
          coherence_out(i) = 1.0 - abs(real(tiles_in(i) - tiles_in(i-1), c_float)) / 1.0e10
          coherence_out(i) = coherence_out(i) + &
               (1.0 - abs(real(tiles_in(i) - tiles_in(i+1), c_float)) / 1.0e10)
          coherence_out(i) = coherence_out(i) / 2.0
       else if (i > 1) then
          coherence_out(i) = 1.0 - abs(real(tiles_in(i) - tiles_in(i-1), c_float)) / 1.0e10
       else if (i < n) then
          coherence_out(i) = 1.0 - abs(real(tiles_in(i) - tiles_in(i+1), c_float)) / 1.0e10
       else
          coherence_out(i) = 0.5
       end if
       if (coherence_out(i) < 0.0) coherence_out(i) = 0.0
       if (coherence_out(i) > 1.0) coherence_out(i) = 1.0

       ! Novelty: avg difference from all other tiles
       diff_sum = 0
       do j = 1, n
          if (j /= i) diff_sum = diff_sum + abs(tiles_in(i) - tiles_in(j))
       end do
       nov_raw = real(diff_sum, c_float) / real(max(n-1, 1), c_float) / 1.0e9
       if (nov_raw > 1.0) nov_raw = 1.0
       novelty_out(i) = nov_raw
       if (novelty_out(i) < 0.0) novelty_out(i) = 0.0

       ! Connectivity: placeholder based on position
       connectivity_out(i) = 0.3 + 0.7 * real(mod(i, 5), c_float) / 4.0
       if (connectivity_out(i) > 1.0) connectivity_out(i) = 1.0

       ! Age: normalized (newest=1.0)
       age_out(i) = real(ages(i), c_float) / real(max_age, c_float)
       if (age_out(i) > 1.0) age_out(i) = 1.0

       ! Value: weighted product of all 5 dimensions
       value_out(i) = coherence_out(i)**DIM_WEIGHTS(1) * &
                      novelty_out(i)**DIM_WEIGHTS(2) * &
                      connectivity_out(i)**DIM_WEIGHTS(3) * &
                      age_out(i)**DIM_WEIGHTS(4) * &
                      (coherence_out(i)*novelty_out(i)*connectivity_out(i)*age_out(i))**DIM_WEIGHTS(5)
       if (value_out(i) > 1.0) value_out(i) = 1.0
       if (value_out(i) < 0.0) value_out(i) = 0.0
    end do
  end subroutine approach_5d_eval

end module approach_5d
