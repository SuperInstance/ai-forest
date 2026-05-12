! Compiled from: telephone_game.flx
! FLUX → Fortran Compiler
! Generates direct Fortran .so calls for all extension opcodes

program flux_program
  use, intrinsic :: iso_c_binding
  implicit none
  integer(c_int32_t) :: i, nr, n
  integer(c_int32_t), allocatable :: a(:), b(:), r(:)

  ! Ignored: PLATO_READ source_room, 1, seed_tile
  call seed_permute(a, size(a), 5, r)
  ! Ignored: PLATO_WRITE results_room, "Telephone game complete. Drift measured."
  ! Ignored: HALT
end program flux_program